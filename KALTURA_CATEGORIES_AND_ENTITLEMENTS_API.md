# Kaltura Categories & Entitlements API

The Categories & Entitlements API covers content organization and user-based content permissions: creating category hierarchies (`KalturaCategory`), managing category membership (`categoryUser`), assigning content to categories (`categoryEntry`), and enforcing content visibility through the entitlement system. Categories are the foundation for Kaltura's entitlement system, which restricts content visibility based on privacy settings, user membership, and KS privileges.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)  
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** Form-encoded POST, `format=1` for JSON responses  
**Services:** `category` (11 actions), `categoryUser` (10 actions), `categoryEntry` (9 actions)  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Authentication | 4.KalturaCategory Object | 5.Category CRUD | 6.Category Hierarchy | 7.Category Membership (categoryUser) | 8.Content Assignment (categoryEntry) | 9.Entitlement System | 10.Bulk Operations | 11.Error Handling | 12.Best Practices | 13.Related Guides -->


# 1. When to Use

- **Department-based content portals** organize media into hierarchical categories with membership-based visibility so each team sees only its own content.  
- **Multi-tenant applications** use category entitlements to isolate content between business units, clients, or partner organizations within a single Kaltura account.  
- **Premium content and subscriptions** gate access to content categories based on paid subscriptions or membership levels.  
- **Group collaboration** channels let team members share and discover content visible only to the group.  
- **Content operations teams** manage large-scale content assignment, category restructuring, and bulk permission updates across thousands of entries.  
- **Application-specific content scoping** uses privacy contexts to separate entitlement rules per application while sharing content across one Kaltura account.


# 2. Prerequisites

- **Kaltura Session (KS):** ADMIN KS (type=2) with `CONTENT_MANAGE_CATEGORY` permission for category and membership operations, `CONTENT_MANAGE_ASSIGN_ENTRY_TO_CATEGORY` for content assignment. See [Session Guide](KALTURA_SESSION_GUIDE.md).  
- **Partner ID and API credentials:** Available from KMC > Settings > Integration Settings.  
- **Service URL:** Set `$KALTURA_SERVICE_URL` to your account's regional endpoint (default: `https://www.kaltura.com/api_v3`).  
- **Entitlement feature:** Category entitlements require activation on your account. Contact your Kaltura representative to enable entitlement if category privacy settings are needed.


# 3. Authentication

All endpoints require an ADMIN KS (type=2) with appropriate permissions:

- **Category CRUD:** `CONTENT_MANAGE_CATEGORY` permission  
- **Category membership:** `CONTENT_MANAGE_CATEGORY` permission  
- **Content assignment:** `CONTENT_MANAGE_ASSIGN_ENTRY_TO_CATEGORY` permission  

Generate an ADMIN KS via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

```bash
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
```


# 4. KalturaCategory Object

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
| `privacyContexts` | string | Comma-separated list of privacy context labels |
| `appearInList` | integer | Who can see this category in listings (see below) |
| `contributionPolicy` | integer | Who can assign content (see below) |
| `inheritanceType` | integer | `1` = INHERIT from parent, `2` = MANUAL |
| `userJoinPolicy` | integer | How users can join (see below) |
| `defaultPermissionLevel` | integer | Default permission for new members |
| `moderation` | integer | `1` = entries require approval before activation |
| `owner` | string | Owner user ID |
| `partnerId` | integer | Partner ID (read-only) |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaCategory"` (read-only) |

## 4.1 Category Status Values

| Value | Name | Description |
|-------|------|-------------|
| 1 | UPDATING | Category is being updated (tree restructuring in progress) |
| 2 | ACTIVE | Normal active category |
| 3 | DELETED | Soft-deleted |
| 4 | PURGED | Permanently removed |

## 4.2 Privacy Levels (KalturaPrivacyType)

| Value | Name | Description |
|-------|------|-------------|
| 1 | ALL | Content is visible to everyone with access to the application |
| 2 | AUTHENTICATED_USERS | Content is visible to authenticated users only (KS with `userId`) |
| 3 | MEMBERS_ONLY | Content is visible only to category members and content owners |

## 4.3 Contribution Policy (KalturaContributionPolicyType)

| Value | Name | Description |
|-------|------|-------------|
| 1 | ALL | Any user can assign content to this category |
| 2 | MEMBERS_WITH_CONTRIBUTION_PERMISSION | Only members with CONTRIBUTOR permission or higher |

## 4.4 Appear In List

| Value | Name | Description |
|-------|------|-------------|
| 1 | PARTNER_ONLY | Visible to all partner users |
| 3 | CATEGORY_MEMBERS_ONLY | Visible only to category members |

## 4.5 User Join Policy (KalturaUserJoinPolicyType)

| Value | Name | Description |
|-------|------|-------------|
| 1 | AUTO_JOIN | Users can add themselves to the category |
| 2 | REQUEST_TO_JOIN | Users can request to join; requires moderator approval |
| 3 | NOT_ALLOWED | By invitation only; users cannot request to join |


# 5. Category CRUD

## 5.1 Create a Category

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
| `category[moderation]` | integer | No | `1` to require entry approval before activation |
| `category[userJoinPolicy]` | integer | No | How users join (1=AUTO, 2=REQUEST, 3=NOT_ALLOWED) |

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

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "category[objectType]=KalturaCategory" \
  -d "category[name]=Onboarding" \
  -d "category[parentId]=$PARENT_CATEGORY_ID" \
  -d "category[description]=Onboarding materials"
```

The response includes the computed `fullName` (e.g., `"Training>Onboarding"`) and `fullIds` (e.g., `"12345>67890"`).

## 5.2 Get a Category

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CATEGORY_ID"
```

Returns the full `KalturaCategory` object. Returns `CATEGORY_NOT_FOUND` if the ID is invalid.

## 5.3 List Categories

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
| `nameEqual` | Exact category name match (case-sensitive, returns first match when duplicates exist) |
| `fullNameStartsWithIn` | Full path prefix match (e.g., `"Training>"`) |
| `ancestorIdIn` | Categories under any of these ancestor IDs |
| `freeText` | Free-text search across name, description, tags |
| `tagsLike` | Tags match (OR) |
| `referenceIdEqual` | Exact reference ID match |
| `statusEqual` | Filter by status (1=UPDATING, 2=ACTIVE, 3=DELETED) |
| `privacyEqual` | Filter by privacy level |
| `privacyIn` | Comma-separated privacy levels |
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

## 5.4 Update a Category

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CATEGORY_ID" \
  -d "category[objectType]=KalturaCategory" \
  -d "category[description]=Updated training materials" \
  -d "category[tags]=training,updated"
```

Fields not included remain unchanged. Response: Full updated `KalturaCategory` object.

## 5.5 Delete a Category

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CATEGORY_ID"
```

Deletes the category. Child categories are also deleted. Entries assigned to the category are unlinked (not deleted).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Category ID to delete |
| `moveEntriesToParentCategory` | integer | No | `1` to move entries to parent before deleting |

## 5.6 Clone a Category Branch

```
POST /service/category/action/clone
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CATEGORY_ID" \
  -d "cloneOptions[objectType]=KalturaCategoryClone"
```

Duplicates the category and its entire subtree under the same parent as the source. Cloned categories receive new IDs while preserving hierarchy structure, names, and settings.


# 6. Category Hierarchy

Categories form a tree structure via the `parentId` field. The API automatically computes path fields:

| Field | Example | Description |
|-------|---------|-------------|
| `parentId` | `12345` | Direct parent category ID (`0` for root) |
| `fullName` | `"Media>Training>Onboarding"` | Full path of names separated by `>` |
| `fullIds` | `"100>12345>67890"` | Full path of IDs separated by `>` |
| `depth` | `2` | Distance from root (`0` for root categories) |

## 6.1 Move a Category

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/move" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryIds=$CATEGORY_ID" \
  -d "targetCategoryParentId=$TARGET_PARENT_CATEGORY_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `categoryIds` | string | Yes | Comma-separated category IDs to move |
| `targetCategoryParentId` | integer | Yes | New parent category ID |

Moving a category updates `fullName`, `fullIds`, and `depth` for the category and all its descendants. The category status may temporarily become `1` (UPDATING) during the move operation.

## 6.2 Traversal Patterns

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
  -d "filter[parentIdEqual]=$CATEGORY_ID"
```

**List all descendants of a category:**
```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaCategoryFilter" \
  -d "filter[ancestorIdIn]=$CATEGORY_ID"
```

**Find categories by path prefix:**
```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaCategoryFilter" \
  -d "filter[fullNameStartsWithIn]=Training>"
```


# 7. Category Membership (categoryUser)

Category membership controls which users belong to a category. When entitlement is enabled, membership determines who can see content assigned to `MEMBERS_ONLY` categories.

## 7.1 KalturaCategoryUser Object

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

### Permission Levels (KalturaCategoryUserPermissionLevel)

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

## 7.2 Add a Member

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryUser[objectType]=KalturaCategoryUser" \
  -d "categoryUser[categoryId]=$CATEGORY_ID" \
  -d "categoryUser[userId]=jane.doe@example.com" \
  -d "categoryUser[permissionLevel]=3"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `categoryUser[objectType]` | string | Yes | Always `KalturaCategoryUser` |
| `categoryUser[categoryId]` | integer | Yes | Category ID |
| `categoryUser[userId]` | string | Yes | User ID to add |
| `categoryUser[permissionLevel]` | integer | No | Permission level (default: `3` MEMBER) |

Response: Full `KalturaCategoryUser` object with `status=1` (ACTIVE).

## 7.3 Get a Member

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryId=$CATEGORY_ID" \
  -d "userId=jane.doe@example.com"
```

## 7.4 List Members

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaCategoryUserFilter" \
  -d "filter[categoryIdEqual]=$CATEGORY_ID" \
  -d "pager[pageSize]=50"
```

Filter fields (KalturaCategoryUserFilter):

| Field | Description |
|-------|-------------|
| `categoryIdEqual` | Members of a specific category |
| `categoryIdIn` | Members of multiple categories |
| `userIdEqual` | Categories a specific user belongs to |
| `userIdIn` | Categories for multiple users |
| `permissionLevelEqual` | Filter by permission level |
| `statusEqual` | Filter by membership status |
| `orderBy` | `+createdAt`, `-createdAt` |

## 7.5 Update a Member

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryId=$CATEGORY_ID" \
  -d "userId=jane.doe@example.com" \
  -d "categoryUser[objectType]=KalturaCategoryUser" \
  -d "categoryUser[permissionLevel]=2"
```

## 7.6 Delete a Member

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryId=$CATEGORY_ID" \
  -d "userId=jane.doe@example.com"
```

## 7.7 Activate / Deactivate a Member

Activate a pending or deactivated member:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/activate" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryId=$CATEGORY_ID" \
  -d "userId=jane.doe@example.com"
```

Deactivate an active member (preserves the membership record):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/deactivate" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryId=$CATEGORY_ID" \
  -d "userId=jane.doe@example.com"
```


# 8. Content Assignment (categoryEntry)

Assign media entries to categories to organize content and enforce entitlement rules.

## 8.1 KalturaCategoryEntry Object

| Field | Type | Description |
|-------|------|-------------|
| `categoryId` | integer | Category ID |
| `entryId` | string | Entry ID |
| `status` | integer | `1` = PENDING, `2` = ACTIVE, `3` = DELETED, `4` = REJECTED |
| `createdAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaCategoryEntry"` (read-only) |

## 8.2 Assign an Entry to a Category

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryEntry[objectType]=KalturaCategoryEntry" \
  -d "categoryEntry[categoryId]=$CATEGORY_ID" \
  -d "categoryEntry[entryId]=$KALTURA_ENTRY_ID"
```

Response: Full `KalturaCategoryEntry` object with `status=2` (ACTIVE), or `status=1` (PENDING) if the category has moderation enabled and the user lacks MODERATOR permission.

## 8.3 List Category Entries

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaCategoryEntryFilter" \
  -d "filter[categoryIdEqual]=$CATEGORY_ID" \
  -d "pager[pageSize]=50"
```

Filter fields (KalturaCategoryEntryFilter):

| Field | Description |
|-------|-------------|
| `categoryIdEqual` | Entries in a specific category |
| `categoryIdIn` | Entries in multiple categories |
| `entryIdEqual` | Categories for a specific entry |
| `statusEqual` | Filter by status (1=PENDING, 2=ACTIVE, 3=DELETED, 4=REJECTED) |
| `orderBy` | `+createdAt`, `-createdAt` |

## 8.4 Delete a Category Entry

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "categoryId=$CATEGORY_ID"
```

Removes the entry from the category. The entry itself is not deleted.

## 8.5 Moderate Category Entries

When a category has `moderation=1`, new entry assignments enter `PENDING` status. Moderators and managers can approve or reject. For full moderation workflows including user flagging and AI-powered content screening, see the [Moderation API Guide](KALTURA_MODERATION_API.md).

**Activate (approve) a pending entry:**
```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/activate" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "categoryId=$CATEGORY_ID"
```

**Reject a pending entry:**
```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/reject" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "categoryId=$CATEGORY_ID"
```

## 8.6 Sync Privacy Context

Synchronize the privacy context for entries in a category after changing the category's `privacyContext`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/syncPrivacyContext" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "categoryId=$CATEGORY_ID"
```


# 9. Entitlement System

Entitlement is Kaltura's mechanism for restricting content visibility based on category membership. It combines category privacy settings, user membership, and KS privileges.

## 9.1 How Entitlement Works

Content entitlements govern which users can see which entries. Entitlements are configured at the category level by setting a **privacy context** (`privacyContext` field) -- a free-text label (English characters, no commas or spaces) that identifies the application context.

Applications such as Content Hubs use entitlements to implement "authenticated content channels."

1. **Category privacy** (`privacy` field) sets the baseline visibility rule.  
2. **Category membership** (`categoryUser`) determines which users have access to `MEMBERS_ONLY` categories.  
3. **KS privileges** control whether entitlement is enforced and which privacy contexts are applied.  
4. **Content owner** always has access to their own content regardless of category settings.  

## 9.2 KS Privileges for Entitlement

| Privilege | Description |
|-----------|-------------|
| `enableentitlement` | Activates entitlement enforcement for this session |
| `privacycontext:LABEL` | Sets the privacy context to match against category `privacyContext` values |
| `disableentitlement` | Explicitly disables entitlement (default for ADMIN KS) |
| `disableentitlementforentry:ENTRY_ID` | Bypasses entitlement for a specific entry |

Generate a USER KS with entitlement:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "type=0" \
  -d "userId=jane.doe@example.com" \
  -d "privileges=enableentitlement,privacycontext:myapp"
```

## 9.3 Entitlement Enforcement Decision Flow

The server evaluates content access in this order (first match wins):

| Step | Check | Result if True |
|------|-------|----------------|
| 1 | Entitlement disabled for this entry by widget/feed services | **ALLOWED** |
| 2 | Account's `defaultEntitlementEnforcement` is FALSE | **ALLOWED** |
| 3 | KS has `disableentitlement` OR `disableentitlementforentry` matching this entry | **ALLOWED** |
| 4 | KS `userId` is the entry owner | **ALLOWED** |
| 5 | KS `userId` has edit or publish permission on the entry | **ALLOWED** |
| 6 | Entry is NOT associated with any categories | **ALLOWED** |
| 7 | ALL of the entry's categories have `privacyContext = null` | **ALLOWED** |
| 8 | KS `privacycontext` matches one of the entry's categories' `privacyContext` AND `category.privacy` is ALL (1) | **ALLOWED** |
| 9 | KS `privacycontext` matches AND `category.privacy` is AUTHENTICATED_USERS (2) AND KS has valid `userId` | **ALLOWED** |
| 10 | KS `privacycontext` matches AND `category.privacy` is MEMBERS_ONLY (3) AND `userId` is a category member | **ALLOWED** |
| 11 | None of the above conditions met | **DENIED** |

## 9.4 Content Visibility with Multiple Categories

When an entry is assigned to multiple categories, the **least restrictive** privacy setting determines access. If an entry is in both a `MEMBERS_ONLY` category and an `ALL` category within the same privacy context, the entry is accessible to everyone.

## 9.5 Privacy Context Configuration

Privacy context is a free-text label that ties categories to applications:

- Assign the same `privacyContext` to an entire category branch to scope entitlement per application  
- Use `privacyContexts` (plural) for multiple comma-separated labels when a category serves multiple applications  
- The KS `privacycontext` privilege must match the category's `privacyContext` for entitlement to be evaluated  
- Categories without a `privacyContext` are not subject to entitlement enforcement  

## 9.6 Account-Level Entitlement Configuration

The `defaultEntitlementEnforcement` property on `KalturaPartner` controls global enforcement:

- **true (default):** Entitlement is enforced. API calls must provide a KS with the correct `privacycontext` and a `userId` who is a member of the category.  
- **false:** Entitlement is not enforced by default. Any valid KS can access content. The application is responsible for implementing its own entitlement logic.

## 9.7 Setting Up Entitlement -- Complete Walkthrough

1. Create a category with `privacy=3` (MEMBERS_ONLY) and a `privacyContext`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "category[objectType]=KalturaCategory" \
  -d "category[name]=Premium Content" \
  -d "category[privacy]=3" \
  -d "category[privacyContext]=myapp"
```

2. Add users as members of the category:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryUser[objectType]=KalturaCategoryUser" \
  -d "categoryUser[categoryId]=$CATEGORY_ID" \
  -d "categoryUser[userId]=jane.doe@example.com" \
  -d "categoryUser[permissionLevel]=3"
```

3. Assign entries to the category:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryEntry[objectType]=KalturaCategoryEntry" \
  -d "categoryEntry[categoryId]=$CATEGORY_ID" \
  -d "categoryEntry[entryId]=$KALTURA_ENTRY_ID"
```

4. Generate a user KS with entitlement for the matching privacy context:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "type=0" \
  -d "userId=jane.doe@example.com" \
  -d "privileges=enableentitlement,privacycontext:myapp"
```

Only `jane.doe@example.com` (a category member) can see entries in this category when using this KS. Other users with entitlement enabled for the same `privacycontext` who are not category members cannot see the entries.

## 9.8 Backward Compatibility Note

The `KalturaBaseEntry` exposes `categories` and `categoriesIds` properties. These properties work only when categories are NOT configured with entitlement settings. Use the `categoryEntry` service to manage category assignments in all cases.


# 10. Bulk Operations

Use bulk upload actions to create categories, assign members, or assign entries in batch via CSV.

## 10.1 Bulk Category Creation

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/addFromBulkUpload" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "bulkUploadData[objectType]=KalturaBulkUploadCsvJobData" \
  --form "fileData=@categories.csv"
```

**CSV columns:** `name`, `parentId`, `referenceId`, `description`, `tags`, `privacy`, `contributionPolicy`, `appearInList`, `privacyContext`

Response: A `KalturaBulkUpload` job object.

## 10.2 Bulk Membership Assignment

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/addFromBulkUpload" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "bulkUploadData[objectType]=KalturaBulkUploadCsvJobData" \
  --form "fileData=@category_members.csv"
```

**CSV columns:** `categoryId`, `userId`, `permissionLevel`, `status`

## 10.3 Bulk Content Assignment

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/addFromBulkUpload" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "bulkUploadData[objectType]=KalturaBulkUploadCsvJobData" \
  --form "fileData=@category_entries.csv"
```

**CSV columns:** `categoryId`, `entryId`

## 10.4 Tracking Bulk Job Status

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


# 11. Error Handling

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
| `MAX_CATEGORIES_FOR_ENTRY_REACHED` | Entry already assigned to 32 categories (default limit) |
| `INVALID_USER_ID` | User ID does not exist |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (HTTP 400, `CATEGORY_NOT_FOUND`, `INVALID_ENTRY_ID`), fix the request before retrying.


# 12. Best Practices

- **Design hierarchy before creating categories.** Plan your category tree structure in advance. Moving categories later triggers a full path recalculation for all descendants.  
- **Use `referenceId` for external system mapping.** Store external system IDs in `referenceId` to simplify integration and avoid needing to track Kaltura category IDs.  
- **Delete children before parents.** When cleaning up category trees, delete child categories first. Deleting a parent cascades to children, but explicit ordering gives you more control.  
- **Use `privacyContext` to segment entitlement.** Assign different `privacyContext` labels to different category trees so you can enable entitlement for specific contexts without affecting others.  
- **Use `categoryUser` for fine-grained permissions.** Permission levels (MANAGER, MODERATOR, CONTRIBUTOR, MEMBER) provide granular control over what each user can do within a category.  
- **Prefer `enableentitlement` in USER KS.** ADMIN KS has entitlement disabled by default. For production playback, generate USER KS (type=0) with `enableentitlement` and the appropriate `privacycontext`.  
- **32 categories per entry limit.** An entry can be assigned to a maximum of 32 categories. Accounts with `FEATURE_DISABLE_CATEGORY_LIMIT` get 1000. Plan your category hierarchy accordingly.  
- **Least-restrictive wins.** When an entry is in multiple categories, the least restrictive privacy setting determines access. Design your category assignments with this in mind.  
- **Use `contributionPolicy=2` with `moderation=1` for moderated categories.** This ensures only authorized users can suggest content, and moderators approve additions.  
- **Use `userJoinPolicy` to control membership.** `AUTO_JOIN` for open categories, `REQUEST_TO_JOIN` for moderated membership, `NOT_ALLOWED` for invitation-only.  


# 13. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — `enableentitlement`, `privacycontext`, `disableentitlement` KS privileges  
- **[Access Control API](KALTURA_ACCESS_CONTROL_API.md)** — IP, country, domain, scheduling restrictions on content delivery (complementary to entitlement)  
- **[User Management API](KALTURA_USER_MANAGEMENT_API.md)** — Users for category membership (`categoryUser` references KalturaUser IDs)  
- **[eSearch API](KALTURA_ESEARCH_API.md)** — Search entries by category assignment, search categories  
- **[Agents Manager API](KALTURA_AGENTS_MANAGER_API.md)** — `ENTRY_ADDED_TO_CATEGORY` trigger for AI agent workflows  
- **[Webhooks API](KALTURA_EVENT_NOTIFICATIONS_WEBHOOK_AND_EMAIL_API.md)** — Category event notifications (category created, entry assigned, etc.)  
- **[Moderation API](KALTURA_MODERATION_API.md)** — Content moderation queue and approval workflows  
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Entitlement determines content visibility in player; access control affects playback  
- **[Content Delivery API](KALTURA_CONTENT_DELIVERY_API.md)** — Delivery URLs where access control is enforced  
- **[Distribution API](KALTURA_DISTRIBUTION_API.md)** — Category-based content scoping for distribution profiles  
- **[Syndication API](KALTURA_SYNDICATION_API.md)** — Category filters for syndication feed content  
- **[Gamification API](KALTURA_GAMIFICATION_API.md)** — Category-based content scoping for gamification rules  

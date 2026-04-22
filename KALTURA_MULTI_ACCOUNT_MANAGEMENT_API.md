# Kaltura Multi-Account Management API

Kaltura's multi-account model enables organizations to create and manage hierarchies of accounts — a parent account that controls one or more child accounts. Each child account is fully independent (its own content, users, settings, and partner ID) while the parent retains administrative oversight and cross-account analytics.

**Base URL:** `https://www.kaltura.com/api_v3`  
**Auth:** Admin KS on the parent account for management operations  
**Format:** Form-encoded POST, `format=1` for JSON responses  

<!-- Sections: 1.When to Use Multi-Account Management | 2.Prerequisites | 3.Sub-Account Creation | 4.Sub-Account Management | 5.Cross-Account Authentication | 6.Cross-Account Analytics | 7.Error Handling | 8.Best Practices | 9.Related Guides -->


# 1. When to Use Multi-Account Management

Multi-account management solves organizational challenges where a single Kaltura account is insufficient:

| Scenario | Why Multi-Account |
|----------|-------------------|
| **Enterprise with divisions** | Each division manages its own content library independently, while corporate HQ monitors usage and analytics across all divisions |
| **Reseller / channel partner** | A Kaltura reseller provisions separate accounts for each customer while maintaining centralized billing and usage reporting |
| **SaaS platform embedding Kaltura** | Each tenant gets an isolated Kaltura account with its own content, users, and permissions — the platform manages them all from one parent |
| **Educational institution** | Separate accounts per department or campus with centralized administration |

A multi-account setup consists of:

- **Parent account** — The administrative account that creates and manages child accounts  
- **Child accounts** — Sub-accounts, each with their own partner ID, content library, users, and configuration  

The parent account can:  
- Create new child accounts via `partner.register`  
- Authenticate as any child account via `session.impersonate`  
- Aggregate analytics across all child accounts using cross-account report variants  
- Manage child account settings and permissions  

Multi-account analytics require the `FEATURE_MULTI_ACCOUNT_ANALYTICS` permission (ID 1130) on the parent account. Contact your Kaltura account manager to enable this.

# 2. Prerequisites

- An ADMIN KS (type=2) on the parent account with sub-account management permissions (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
- The multi-account feature enabled on your parent account — contact your Kaltura account manager to provision child account creation  
- For cross-account analytics: the `FEATURE_MULTI_ACCOUNT_ANALYTICS` permission (ID 1130) enabled on the parent account  


# 3. Sub-Account Creation

Create a child account linked to the parent using `partner.register`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/partner/action/register" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "partner[objectType]=KalturaPartner" \
  -d "partner[name]=Child Account - Division A" \
  -d "partner[adminName]=Admin User" \
  -d "partner[adminEmail]=admin@division-a.example.com" \
  -d "partner[description]=Division A sub-account" \
  -d "partner[country]=US"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `partner[objectType]` | string | Yes | Always `KalturaPartner` |
| `partner[name]` | string | Yes | Display name for the child account |
| `partner[adminName]` | string | Yes | Name of the account admin user |
| `partner[adminEmail]` | string | Yes | Admin email — receives account credentials |
| `partner[description]` | string | No | Description of the child account |
| `partner[country]` | string | No | Two-letter country code (e.g., `US`, `GB`, `DE`) |
| `partner[website]` | string | No | Organization website URL |

**Response:**

```json
{
  "id": 5678901,
  "name": "Child Account - Division A",
  "adminEmail": "admin@division-a.example.com",
  "status": 1,
  "partnerParentId": 1234567,
  "objectType": "KalturaPartner"
}
```

| Response Field | Type | Description |
|---------------|------|-------------|
| `id` | integer | Partner ID of the newly created child account |
| `name` | string | Account display name |
| `adminEmail` | string | Admin email address |
| `status` | integer | Account status: 1 = ACTIVE, 2 = BLOCKED |
| `partnerParentId` | integer | Parent account's partner ID — set automatically |
| `adminSecret` | string | Admin secret for the child account (returned only on creation) |

The `partnerParentId` field links the child to the parent account. This relationship is set automatically when a parent account creates the child.

> **Testing note:** `partner.register` creates a real child account that cannot be deleted via the API. It requires the calling account to have sub-account creation permissions (`SERVICE_FORBIDDEN` is returned otherwise). Test this action only when you intend to create a permanent child account. Verify your account has the necessary permissions before calling this endpoint.


# 4. Sub-Account Management

## 4.1 List Child Accounts

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/partner/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaPartnerFilter" \
  -d "filter[statusIn]=1,2" \
  -d "pager[pageSize]=50" \
  -d "pager[pageIndex]=1"
```

| Filter Parameter | Type | Description |
|-----------------|------|-------------|
| `filter[objectType]` | string | Always `KalturaPartnerFilter` |
| `filter[statusIn]` | string | Comma-separated status values: 1 = ACTIVE, 2 = BLOCKED |
| `filter[idIn]` | string | Comma-separated partner IDs to filter |
| `filter[idGreaterThanOrEqual]` | integer | Filter by minimum partner ID |
| `filter[partnerParentIdEqual]` | integer | Filter children of a specific parent |
| `pager[pageSize]` | integer | Results per page (max 500) |
| `pager[pageIndex]` | integer | Page number (1-based) |

**Response:** `{ "objects": [...], "totalCount": N }` — each object is a `KalturaPartner` with `id`, `name`, `status`, `partnerParentId`, `adminEmail`, and configuration fields.

## 4.2 Get Child Account Details

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/partner/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CHILD_PARTNER_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Partner ID of the child account to retrieve |

Returns the full `KalturaPartner` object with account configuration, status, features, and parent relationship.

## 4.3 Update Child Account

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/partner/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "partner[objectType]=KalturaPartner" \
  -d "partner[name]=Updated Division Name" \
  -d "partner[description]=Updated description" \
  -d "id=$CHILD_PARTNER_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Partner ID of the child account to update |
| `partner[objectType]` | string | Yes | Always `KalturaPartner` |
| `partner[name]` | string | No | Updated display name |
| `partner[description]` | string | No | Updated description |
| `partner[adminEmail]` | string | No | Updated admin email |
| `partner[country]` | string | No | Updated country code |


# 5. Cross-Account Authentication

## 5.1 session.impersonate

Generate a KS scoped to a child account while authenticated as the parent. This lets the parent operate as if it were the child account — managing content, users, and running reports.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/impersonate" \
  -d "format=1" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "impersonatedPartnerId=$CHILD_PARTNER_ID" \
  -d "userId=admin" \
  -d "type=2" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "expiry=1800"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `secret` | string | Yes | Admin secret of the **parent** account |
| `impersonatedPartnerId` | integer | Yes | Partner ID of the child account to impersonate |
| `userId` | string | No | User ID for the impersonated session (default: calling user) |
| `type` | integer | Yes | KS type: 0 = USER, 2 = ADMIN |
| `partnerId` | integer | Yes | Partner ID of the **parent** account |
| `expiry` | integer | No | Session TTL in seconds (default: 86400) |
| `privileges` | string | No | KS privileges (e.g., `disableentitlement`, `edit:*`) |

**Response:** Returns a KS string scoped to the child account. Use this KS for any API calls that should execute in the child account context.

**Use cases:**  
- Admin tools that manage content across all child accounts  
- Running standard reports scoped to a specific child account  
- Provisioning users or content in a child account from a centralized system  

> The impersonated KS operates with the same permissions as a native admin KS on the child account. Use short TTLs and scope privileges minimally.  
> `session.impersonate` only works between parent and child accounts — you cannot impersonate accounts that are not your children.


# 6. Cross-Account Analytics

Cross-account analytics let the parent account aggregate data across all child accounts without impersonating each one individually.

## 6.1 Multi-Account Report Types

Every standard VOD report has a multi-account counterpart in the 20000 range. These reports automatically aggregate across all child accounts linked to the parent.

| Multi-Account Report ID | Standard Counterpart | Report Name |
|-------------------------|---------------------|-------------|
| 20001 | 1 | Content Dropoff |
| 20002 | 2 | Content Interactions |
| 20003 | 3 | Content Contributions |
| 20005 | 5 | Platforms |
| 20006 | 6 | Operating Systems |
| 20007 | 7 | Browsers |
| 20010 | 10 | Top Content |
| 20011 | 11 | Unique Users (Play) |
| 20012 | 12 | Map Overlay (Country) |
| 20013 | 13 | Map Overlay (Region) |
| 20014 | 14 | Map Overlay (City) |
| 20018 | 18 | Top Syndication |
| 20019 | 19 | Partner Usage |
| 20020 | 20 | Platforms (Extended) |
| 20021 | 21 | Operating Systems (Extended) |
| 20022 | 22 | Browsers (Extended) |
| 20023 | 23 | Top Playback Context |

## 6.2 Aggregated Reports

Query a multi-account report from the parent account to get data aggregated across all child accounts:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=20010" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "pager[pageSize]=100" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `reportType` | integer | Yes | Multi-account report ID (20001-20023) or cross-partner report ID |
| `reportInputFilter[objectType]` | string | Yes | Always `KalturaEndUserReportInputFilter` |
| `reportInputFilter[fromDate]` | integer | Yes | Start of date range as Unix timestamp |
| `reportInputFilter[toDate]` | integer | Yes | End of date range as Unix timestamp |
| `pager[pageSize]` | integer | No | Results per page (default: 25, max: 500) |
| `pager[pageIndex]` | integer | No | Page number, 1-based (default: 1) |
| `objectIds` | string | No | Comma-separated partner IDs to filter to specific child accounts |
| `responseOptions[objectType]` | string | No | Always `KalturaReportResponseOptions` |
| `responseOptions[delimiter]` | string | No | Column delimiter in response (default: `,`, recommended: `\|`) |

The `partnerParentId` dimension in the analytics backend links child account data to the parent, enabling aggregation without explicit child account enumeration.

## 6.3 Per-Account Usage Reports

Use cross-partner report types to break down usage by child account:

```bash
# Partner usage breakdown (report type 201)
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTotal" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=201" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

Filter to specific child accounts using `objectIds`:

```bash
# Usage for specific child accounts only
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=60" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "objectIds=CHILD_PARTNER_ID_1,CHILD_PARTNER_ID_2" \
  -d "pager[pageSize]=100" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

**Cross-partner report types:**

| Report Type | Description | Key Columns |
|-------------|-------------|-------------|
| 60 | Per-account engagement breakdown | `partner_id`, `count_plays`, `sum_time_viewed`, `count_loads` |
| 201 | Bandwidth and storage totals per account | `partner_id`, `bandwidth_consumption`, `average_storage`, `combined_bandwidth_storage` |
| 19 | Partner usage summary | `partner_id`, `count_plays`, `count_loads`, `count_contributions` |
| 42 | Top content across accounts | `entry_id`, `partner_id`, `count_plays`, `sum_time_viewed` |

All report calls use the same parameters: `reportType`, `reportInputFilter` (with `fromDate`/`toDate` as Unix timestamps), `pager`, and `responseOptions`. See [Analytics Reports Guide](KALTURA_ANALYTICS_REPORTS_API.md) for the full `report.getTable`/`report.getTotal` parameter reference.

## 6.5 Report Response Format

Report responses use **pipe-delimited strings** for both `header` and `data` fields. Rows within `data` are separated by semicolons.

### report.getTable Response Structure

```json
{
  "header": "partner_id|count_plays|sum_time_viewed|count_loads",
  "data": "5678901|150|3600|400;5678902|75|1800|200",
  "totalCount": 2,
  "objectType": "KalturaReportTable"
}
```

| Field | Format | Description |
|-------|--------|-------------|
| `header` | Pipe-delimited string | Column names separated by `\|` |
| `data` | Semicolon-separated rows, pipe-delimited columns | Each row is separated by `;`, and columns within each row are separated by `\|` |
| `totalCount` | Integer | Total rows available (for pagination) |

### report.getTotal Response Structure

```json
{
  "header": "count_plays|unique_known_users|sum_time_viewed",
  "data": "1250|340|45600",
  "objectType": "KalturaReportTotal"
}
```

`report.getTotal` returns a single row (no semicolon separators in `data`).

### Parsing Pipe-Delimited Report Data

Parse the `header` and `data` fields by splitting on the delimiter characters:

```bash
# Example: Parse a multi-account report response
RESPONSE=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=20010" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "pager[pageSize]=100" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|")

# Extract header and data using jq
HEADER=$(echo "$RESPONSE" | jq -r '.header')
DATA=$(echo "$RESPONSE" | jq -r '.data')
TOTAL=$(echo "$RESPONSE" | jq -r '.totalCount')

# Parse header into column names
IFS='|' read -ra COLUMNS <<< "$HEADER"
echo "Columns: ${COLUMNS[*]}"

# Parse each row
IFS=';' read -ra ROWS <<< "$DATA"
for ROW in "${ROWS[@]}"; do
  IFS='|' read -ra FIELDS <<< "$ROW"
  # Map fields to column names
  for i in "${!COLUMNS[@]}"; do
    echo "  ${COLUMNS[$i]}: ${FIELDS[$i]}"
  done
  echo "---"
done
```

Example output for a multi-account Top Content report (20010):

```
Columns: object_id entry_name count_plays sum_time_viewed
  object_id: 1_abc123
  entry_name: Company Overview
  count_plays: 150
  sum_time_viewed: 3600
---
  object_id: 1_def456
  entry_name: Product Demo
  count_plays: 75
  sum_time_viewed: 1800
---
```

> The `responseOptions[delimiter]` parameter controls the column delimiter in the response. Use `|` (pipe) for consistency. If you set a different delimiter (e.g., `,`), adjust your parsing logic accordingly. Semicolons always separate rows regardless of the column delimiter setting.

## 6.4 Drill-Down into a Child Account

To run standard reports for a specific child account, use `session.impersonate` to get a child-scoped KS, then run any standard report:

```bash
# Step 1: Impersonate the child account
CHILD_KS=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/session/action/impersonate" \
  -d "format=1" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "impersonatedPartnerId=$CHILD_PARTNER_ID" \
  -d "userId=admin" \
  -d "type=2" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "expiry=900" | jq -r '.result // .')

# Step 2: Run a standard report scoped to the child
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$CHILD_KS" \
  -d "format=1" \
  -d "reportType=10" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "pager[pageSize]=50" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```


# 7. Error Handling

| Error Code | Context | Meaning |
|------------|---------|---------|
| `START_SESSION_ERROR` | `session.impersonate` | The target `impersonatedPartnerId` is not a child of the calling account |
| `INVALID_KS` | Any API call | The impersonated KS has expired — generate a new one with `session.impersonate` |
| `SERVICE_FORBIDDEN` | `partner.register` | The calling account lacks permission to create child accounts |
| Empty `objects` array | Multi-account reports (20001-20023) | The parent account does not have `FEATURE_MULTI_ACCOUNT_ANALYTICS` (ID 1130) enabled |


# 8. Best Practices

- **Use `session.impersonate` with short TTLs.** Impersonated sessions should be short-lived (5-15 minutes) and scoped to the specific task.  
- **Prefer multi-account reports for aggregation.** Use multi-account report variants (20001-20023) to get cross-account data in a single call rather than impersonating each child account individually.  
- **Track child account IDs.** Maintain a mapping of child partner IDs to your internal organization structure for report filtering with `objectIds`.  
- **Ensure `FEATURE_MULTI_ACCOUNT_ANALYTICS` is enabled.** This permission (ID 1130) must be active on the parent account. Without it, multi-account reports return empty results.  
- **Use `objectIds` for targeted reports.** Filter cross-partner reports to specific child accounts rather than pulling data for all accounts when you only need a subset.  
- **Use AppTokens per child account.** Create separate AppTokens for each child account integration. This enables independent revocation and audit trails per tenant.


# 9. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation, including `session.impersonate` authentication  
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — Full analytics API reference, report types, and cross-account report variants  
- **[User Management](KALTURA_USER_MANAGEMENT_API.md)** — User provisioning for child accounts  
- **[AppTokens](KALTURA_APPTOKENS_API.md)** — Scoped authentication tokens for child account integrations

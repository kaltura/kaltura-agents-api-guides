# Kaltura eSearch API

Kaltura's eSearch API, powered by Elasticsearch, provides flexible full-text search across media entries, categories, users, captions, custom metadata, cue points, and more — all in a single API call.

**Base URL:** `https://www.kaltura.com/api_v3`  
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** Form-encoded POST (`application/x-www-form-urlencoded`), `format=1` for JSON responses  

# 1. API Endpoint & Structure

* **Service:** `elasticsearch_esearch`
* **Primary Actions:**
    * `searchEntry`: Search across media entries and their related data.
    * `searchCategory`: Search category objects.
    * `searchUser`: Search user objects.
    * `searchGroup`: Search group objects.
* **Endpoint Format:** `$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/{action}`
* **HTTP Method:** `POST`
* **Data Format:** `application/x-www-form-urlencoded` (Form Data). Nested parameters use standard array notation (e.g., `param[key][subkey]=value`).


# 2. Authentication

Include the `ks` as part of the POST form data:

```bash
-d "ks=$KALTURA_KS"
-d "format=1"
```


# 3. Core Request Parameters & Objects

Requests are built using specific Kaltura objects passed as form parameters.

* **`ks`** (String): Your valid Kaltura Session string.
* **`format`** (Integer): Response format. Use `1` for JSON (recommended).
* **`searchParams`** (Object): The primary container for your search criteria. The specific type depends on the action (e.g., `KalturaESearchEntryParams` for `searchEntry`).
    * **`searchOperator`** (Object, e.g., `KalturaESearchEntryOperator`): Defines the core search logic.
        * `operator` (Enum `KalturaESearchOperatorType`): How to combine the `searchItems`.
            * `1` (`AND_OP`): All conditions must be met.
            * `2` (`OR_OP`): At least one condition must be met.
            * `3` (`NOT_OP`): Excludes items matching the nested conditions (typically used within an AND/OR operator).
        * `searchItems` (Array): An array of one or more Search Item objects (see Section 5) defining the specific criteria.
    * **`orderBy`** (Object `KalturaESearchOrderBy`, optional): Defines sorting.
        * `orderItems` (Array of `KalturaESearchOrderByItem`): Each item specifies:
            * `sortField` (Enum, e.g., `KalturaESearchEntryOrderByFieldName`): Field like `created_at`, `plays`, `name`, `last_played_at`.
            * `sortOrder` (Enum `KalturaESearchSortOrder`): `asc` or `desc`.
    * **`aggregations`** (Object `KalturaESearchAggregation`, optional): Defines aggregations (see Example G in Section 7).
        * `aggregations` (Array of `KalturaESearchAggregationItem`): Each item specifies:
            * `fieldName` (Enum, e.g., `KalturaESearchEntryAggregateByFieldName`): Field to group by, like `media_type`.
            * `size` (Integer): Max number of aggregation buckets to return.
* **`pager`** (Object `KalturaPager`, optional): Controls pagination.
    * `pageIndex` (Integer): The page number to retrieve (starts at 1).
    * `pageSize` (Integer): Number of results per page (default 30, max 500).

# 4. Search Item (`searchItems`) Deep Dive

These objects define *what* you're searching for within the `searchOperator.searchItems` array.

**Common Search Item Types:**

* `KalturaESearchUnifiedItem`: Searches across multiple standard fields (name, description, tags, captions, etc.). Ideal for general keyword searches.
* `KalturaESearchEntryItem`: Targets specific fields within a `KalturaMediaEntry` or `KalturaBaseEntry`.
* `KalturaESearchCaptionItem`: Searches specifically within caption content.
* `KalturaESearchEntryMetadataItem`: Searches within custom metadata fields linked to entries.
* `KalturaESearchCuePointItem`: Searches within data fields of cue points linked to entries.
* *(Similar items exist for Category, User, Group searches, e.g., `KalturaESearchCategoryItem`)*

**Key Properties for Search Items:**

* `objectType` (String): *Required.* The specific Kaltura class name (e.g., `"KalturaESearchUnifiedItem"`).
* `searchTerm` (String): The keyword, phrase, or value to search for. Ignored if `itemType` is `EXISTS` or `RANGE`.
* `itemType` (Enum `KalturaESearchItemType`): *Required.* Defines the matching strategy:
    * `1` (`EXACT_MATCH`): Matches the exact term (case-insensitive, tokenized).
    * `2` (`PARTIAL`): Allows partial word matches and utilizes synonym expansion (e.g., 'delicious' finds 'yummy').
    * `3` (`STARTS_WITH`): Matches terms that begin with the `searchTerm`.
    * `4` (`EXISTS`): Checks if the specified `fieldName` has *any* value.
    * `5` (`RANGE`): Performs a range query using the `range` property.
* `fieldName` (Enum): *Required for non-Unified items.* Specifies the target field (e.g., `KalturaESearchEntryFieldName::NAME`, `KalturaESearchCaptionFieldName::CONTENT`).
* `addHighlight` (Boolean, optional): Default `false`. Set to `true` to receive highlighted snippets in the response showing where matches occurred.
* `range` (Object `KalturaESearchRange`): *Required if `itemType` is `RANGE`.* Defines the boundaries:
    * `greaterThanOrEqual` (Integer)
    * `lessThanOrEqual` (Integer)
    * `greaterThan` (Integer)
    * `lessThan` (Integer)
    * *(Use epoch timestamps in seconds for date fields like `created_at`)*.
* `metadataProfileId` (Integer, for Metadata items): ID of the metadata profile to search within.
* `xpath` (String, optional for Metadata items): Targets a specific XML path within the metadata. If omitted, searches all fields in the profile.

# 5. API Response Format (JSON)

The API typically returns a JSON object structured as follows:

* **`totalCount`** (Integer): The total number of results matching the query, irrespective of pagination.
* **`objects`** (Array): An array where each element represents a matched item (e.g., an entry result).
    * **`object`** (Object): The core Kaltura object itself (e.g., `KalturaMediaEntry`, `KalturaCategory`) containing its standard properties (`id`, `name`, `description`, `createdAt`, etc.).
    * **`highlight`** (Array, optional): An array of `KalturaESearchHighlight` objects, present if `addHighlight` was requested.
        * `fieldName` (String): The field where a match was found (e.g., `"name"`, `"description"`, `"captions_content"`).
        * `hits` (Array): An array of `KalturaString` objects, each containing:
            * `value` (String): The text snippet with the match highlighted via `<em>...</em>` tags.
    * **`itemsData`** (Array, optional): Contains more granular results when searching within nested data like captions or metadata. Each element is a `KalturaESearchItemDataResult`.
        * `totalCount` (Integer): Number of specific items found (e.g., matching caption lines).
        * `items` (Array): Array of specific data items (e.g., `KalturaESearchCaptionItemData`, `KalturaESearchMetadataItemData`). These objects contain details like the specific caption line text, start/end times, or metadata field values. They might *also* contain their own nested `highlight` array.
        * `itemsType` (String): Indicates the type of items (e.g., `"caption"`, `"metadata"`).
* **`aggregations`** (Array, optional): Present if aggregations were requested. Contains `KalturaESearchAggregationResponseItem` objects.
    * `fieldName` (String): The field used for aggregation (e.g., `"media_type"`).
    * `buckets` (Array): Array of `KalturaESearchAggregationBucket` objects.
        * `value` (String): The specific value for the bucket (e.g., `"1"` for video media type).
        * `count` (Integer): The number of results falling into this bucket.

# 6. Capabilities & Scenarios (with Curl Examples)

Examples pipe to `jq` for readability.

**A. Basic Unified Keyword Search with Highlighting**
* **Goal:** Find entries matching "visual studio code" anywhere, show highlights.
* **Capability:** Unified search, Highlighting, Partial/Synonym matching.
* **Curl:**
    ```bash
    curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
    -d "ks=$KALTURA_KS" \
    -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchUnifiedItem" \
    -d "searchParams[searchOperator][searchItems][0][searchTerm]=visual studio code" \
    -d "searchParams[searchOperator][searchItems][0][itemType]=2" \
    -d "searchParams[searchOperator][searchItems][0][addHighlight]=true" \
    -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
    -d "searchParams[objectType]=KalturaESearchEntryParams" \
    -d "format=1" | jq .
    ```

**Response:**
```json
{
  "totalCount": 42,
  "objects": [
    {
      "object": { "id": "1_abc123", "name": "...", "objectType": "KalturaMediaEntry" },
      "highlight": [{ "fieldName": "name", "hits": "<em>search term</em> in title" }],
      "itemsData": [...]
    }
  ],
  "objectType": "KalturaESearchEntryResponse"
}
```

**B. Field-Specific Search (Entry Name, Starts With)**
* **Goal:** Find entries where the name starts with "AI Hacker".
* **Capability:** Field-specific search, Starts With matching.
* **Curl:**
    ```bash
    curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
    -d "ks=$KALTURA_KS" \
    -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchEntryItem" \
    -d "searchParams[searchOperator][searchItems][0][searchTerm]=AI Hacker" \
    -d "searchParams[searchOperator][searchItems][0][itemType]=3" \
    -d "searchParams[searchOperator][searchItems][0][fieldName]=name" \
    -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
    -d "searchParams[objectType]=KalturaESearchEntryParams" \
    -d "format=1" | jq .
    ```

**C. Multi-Language Caption Search**
* **Goal:** Find entries with the Chinese word 食谱 ("recipe") in captions.
* **Capability:** Multi-language, Field-specific search.
* **Curl:**
    ```bash
    curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
    -d "ks=$KALTURA_KS" \
    -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchCaptionItem" \
    -d "searchParams[searchOperator][searchItems][0][searchTerm]=食谱" \
    -d "searchParams[searchOperator][searchItems][0][itemType]=2" \
    -d "searchParams[searchOperator][searchItems][0][fieldName]=content" \
    -d "searchParams[searchOperator][searchItems][0][addHighlight]=true" \
    -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
    -d "searchParams[objectType]=KalturaESearchEntryParams" \
    -d "format=1" | jq .
    ```

**D. Custom Metadata Search (Specific Field)**
* **Goal:** Find entries where metadata profile ID 653 has the field `/metadata/Field1` exactly matching "recipe".
* **Capability:** Metadata search, XPath targeting, Exact Match.
* **Curl:**
    ```bash
    curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
    -d "ks=$KALTURA_KS" \
    -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchEntryMetadataItem" \
    -d "searchParams[searchOperator][searchItems][0][searchTerm]=recipe" \
    -d "searchParams[searchOperator][searchItems][0][itemType]=1" \
    -d "searchParams[searchOperator][searchItems][0][metadataProfileId]=653" \
    -d "searchParams[searchOperator][searchItems][0][xpath]=/*[local-name()='metadata']/*[local-name()='Field1']" \
    -d "searchParams[searchOperator][searchItems][0][addHighlight]=true" \
    -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
    -d "searchParams[objectType]=KalturaESearchEntryParams" \
    -d "format=1" | jq .
    ```

**E. Complex Logic (AND/NOT)**
* **Goal:** Find entries with "strawberry" in the name AND which do *NOT* have "adding sugar" in the cue point text.
* **Capability:** Complex logic operators, Field-specific search, Cue point search.
* **Curl:**
    ```bash
    curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
    -d "ks=$KALTURA_KS" \
    # Main AND operator combines two items:
    -d "searchParams[searchOperator][operator]=1" \
    -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
    # Item 0: 'strawberry' in name
    -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchEntryItem" \
    -d "searchParams[searchOperator][searchItems][0][itemType]=2" \
    -d "searchParams[searchOperator][searchItems][0][fieldName]=name" \
    -d "searchParams[searchOperator][searchItems][0][searchTerm]=strawberry" \
    # Item 1: Nested NOT operator
    -d "searchParams[searchOperator][searchItems][1][objectType]=KalturaESearchEntryOperator" \
    -d "searchParams[searchOperator][searchItems][1][operator]=3" \
    # Item 1.0 (inside NOT): 'adding sugar' in cue point text
    -d "searchParams[searchOperator][searchItems][1][searchItems][0][objectType]=KalturaESearchCuePointItem" \
    -d "searchParams[searchOperator][searchItems][1][searchItems][0][itemType]=1" \
    -d "searchParams[searchOperator][searchItems][1][searchItems][0][fieldName]=text" \
    -d "searchParams[searchOperator][searchItems][1][searchItems][0][searchTerm]=adding sugar" \
    # End searchParams object
    -d "searchParams[objectType]=KalturaESearchEntryParams" \
    -d "format=1" | jq .
    ```

**F. Date Range Search**
* **Goal:** Find entries created between Jan 1, 2024 (1704067200) and Feb 1, 2024 (1706745600).
* **Capability:** Range searching on date fields.
* **Curl:**
    ```bash
    curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
    -d "ks=$KALTURA_KS" \
    -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchEntryItem" \
    -d "searchParams[searchOperator][searchItems][0][itemType]=5" \
    -d "searchParams[searchOperator][searchItems][0][fieldName]=created_at" \
    -d "searchParams[searchOperator][searchItems][0][range][objectType]=KalturaESearchRange" \
    -d "searchParams[searchOperator][searchItems][0][range][greaterThanOrEqual]=1704067200" \
    -d "searchParams[searchOperator][searchItems][0][range][lessThan]=1706745600" \
    -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
    -d "searchParams[objectType]=KalturaESearchEntryParams" \
    -d "format=1" | jq .
    ```

**G. Aggregation & Sorting**
* **Goal:** Find "visual studio code", aggregate by `media_type`, sort by `last_played_at` (desc).
* **Capability:** Aggregation, Sorting.
* **Curl:**
    ```bash
    curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
    -d "ks=$KALTURA_KS" \
    -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchUnifiedItem" \
    -d "searchParams[searchOperator][searchItems][0][searchTerm]=visual studio code" \
    -d "searchParams[searchOperator][searchItems][0][itemType]=2" \
    -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
    -d "searchParams[objectType]=KalturaESearchEntryParams" \
    -d "searchParams[aggregations][0][objectType]=KalturaESearchEntryAggregationItem" \
    -d "searchParams[aggregations][0][fieldName]=media_type" \
    -d "searchParams[aggregations][0][size]=10" \
    -d "searchParams[orderBy][orderItems][0][objectType]=KalturaESearchOrderByItem" \
    -d "searchParams[orderBy][orderItems][0][sortField]=last_played_at" \
    -d "searchParams[orderBy][orderItems][0][sortOrder]=desc" \
    -d "format=1" | jq .
    ```

# 7. Advanced Topics & Use Cases

* **Aggregations (`searchParams[aggregations]`):**
    * **Use Case:** Get a summary view without retrieving all results, e.g., "Show me the count of videos vs. images matching 'tutorial'".
    * **How:** Specify the field (e.g., `KalturaESearchEntryAggregateByFieldName::MEDIA_TYPE`) in a `KalturaESearchEntryAggregationItem` within the `searchParams`.
    * **Response:** The `aggregations` array in the response will contain buckets with counts for each media type found.
* **Searching Different Object Types:**
    * **Use Case:** Find categories tagged "Education" or users named "John Doe".
    * **How:** Use the appropriate action (`searchCategory`, `searchUser`, `searchGroup`) and the corresponding `searchParams` type (`KalturaESearchCategoryParams`, `KalturaESearchUserParams`, `KalturaESearchGroupParams`). The structure of `searchOperator` and `searchItems` remains similar, but you use object-specific field names (e.g., `KalturaESearchCategoryFieldName::TAGS`, `KalturaESearchUserFieldName::FULL_NAME`).

    **searchCategory example:**
    ```bash
    curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchCategory" \
      -d "ks=$KALTURA_KS" \
      -d "format=1" \
      -d "searchParams[objectType]=KalturaESearchCategoryParams" \
      -d "searchParams[searchOperator][objectType]=KalturaESearchCategoryOperator" \
      -d "searchParams[searchOperator][operator]=1" \
      -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchCategoryItem" \
      -d "searchParams[searchOperator][searchItems][0][fieldName]=name" \
      -d "searchParams[searchOperator][searchItems][0][itemType]=2" \
      -d "searchParams[searchOperator][searchItems][0][searchTerm]=Education"
    ```

    **searchUser example:**
    ```bash
    curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchUser" \
      -d "ks=$KALTURA_KS" \
      -d "format=1" \
      -d "searchParams[objectType]=KalturaESearchUserParams" \
      -d "searchParams[searchOperator][objectType]=KalturaESearchUserOperator" \
      -d "searchParams[searchOperator][operator]=1" \
      -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchUserItem" \
      -d "searchParams[searchOperator][searchItems][0][fieldName]=full_name" \
      -d "searchParams[searchOperator][searchItems][0][itemType]=2" \
      -d "searchParams[searchOperator][searchItems][0][searchTerm]=John"
    ```

    **searchGroup example:**
    ```bash
    curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchGroup" \
      -d "ks=$KALTURA_KS" \
      -d "format=1" \
      -d "searchParams[objectType]=KalturaESearchGroupParams" \
      -d "searchParams[searchOperator][objectType]=KalturaESearchGroupOperator" \
      -d "searchParams[searchOperator][operator]=1" \
      -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchGroupItem" \
      -d "searchParams[searchOperator][searchItems][0][fieldName]=screen_name" \
      -d "searchParams[searchOperator][searchItems][0][itemType]=2" \
      -d "searchParams[searchOperator][searchItems][0][searchTerm]=Engineering"
    ```

    All four actions (`searchEntry`, `searchCategory`, `searchUser`, `searchGroup`) return the same response structure: `{ objects: [...], totalCount, objectType }`. Each object is wrapped in `{ object, itemsData, highlight }`.
* **Nested Queries:**
    * **Use Case:** Combining complex AND/OR/NOT logic as shown in Scenario E.
    * **How:** Place a `KalturaESearchEntryOperator` (or similar) within the `searchItems` array of another operator. This allows nesting conditions (e.g., `A AND (B OR (NOT C))`).

# 8. Edge Cases & Best Practices

* **10,000 Result Limit:** Elasticsearch enforces a 10K result cap (500/page x 20 pages max). To traverse larger result sets, use `KalturaESearchRange` on `created_at` with scroll-forward pagination — move the date window after each 10K batch.
* **Large Result Sets:** Always use the `pager` parameter (`pageIndex`, `pageSize`) to retrieve results in manageable chunks. Iterate through pages by incrementing `pageIndex` until the number of returned objects is less than `pageSize` or zero.
* **Highlighting Context:** Remember that highlights (`<em>` tags) are embedded in the text. You might need to parse or display this HTML carefully. The `itemsData` array provides more context for matches in captions or metadata than the top-level `highlight` array.
* **Partial vs. Exact Match:** `PARTIAL` (`itemType=2`) is powerful due to synonyms but might return less precise results than `EXACT_MATCH` (`itemType=1`). Choose based on the desired recall vs. precision. Use `ignoreSynonym=true` in `searchParams` to disable synonym expansion if needed.
* **NOT Operator Shorthand:** Use the `!` prefix in `freeText` (e.g., `searchTerm=!excluded`) to exclude matches. For structured queries, use `KalturaESearchOperatorType` with `NOT_OP` (`3`).
* **Performance:** Unified searches (`KalturaESearchUnifiedItem`) are convenient but can be slower than targeted searches using specific `fieldName`s (like `NAME` or `CAPTIONS_CONTENT`) because they query more fields. Optimize by specifying fields when possible.
* **Schema Reference:** The Kaltura API schema (XML) is the definitive source for all object structures, properties, enums, and their exact names. Refer to it frequently.

# 9. Key Objects & Enums Quick Reference

* **Params:** `KalturaESearchEntryParams`, `KalturaESearchCategoryParams`, `KalturaESearchUserParams`
* **Operator:** `KalturaESearchEntryOperator` (and variants)
* **Items:** `KalturaESearchUnifiedItem`, `KalturaESearchEntryItem`, `KalturaESearchCaptionItem`, `KalturaESearchEntryMetadataItem`, `KalturaESearchCuePointItem`
* **Response:** `KalturaESearchEntryResponse` (and variants), `KalturaESearchEntryResult` (and variants), `KalturaESearchHighlight`, `KalturaESearchItemDataResult`, `KalturaESearchAggregationResponse`

## Entry Field Names (`KalturaESearchEntryFieldName`)

Use these values in the `fieldName` property of `KalturaESearchEntryItem`:

| Value | Description |
|-------|-------------|
| `id` | Entry ID |
| `name` | Entry display name |
| `description` | Entry description |
| `tags` | Entry tags |
| `admin_tags` | Admin-only tags |
| `reference_id` | External reference ID |
| `credit` | Credit/attribution text |
| `site_url` | Associated site URL |
| `created_at` | Creation timestamp (use RANGE itemType) |
| `updated_at` | Last update timestamp (use RANGE itemType) |
| `last_played_at` | Last playback timestamp (use RANGE itemType) |
| `start_date` | Scheduling start date |
| `end_date` | Scheduling end date |
| `media_type` | Media type (1=video, 2=image, 5=audio) |
| `entry_type` | Entry type (1=media, 7=live, etc.) |
| `moderation_status` | Moderation status value |
| `creator_kuser_id` | Creator user ID |
| `kuser_id` | Owner user ID |
| `plays` | Total play count (use RANGE for numeric filtering) |
| `votes` | Vote count |
| `display_in_search` | Search visibility (0=none, 1=partner, 2=network) |
| `parent_id` | Parent entry ID (for clips/children) |
| `root_id` | Root entry ID |
| `captions_content` | Full-text search within caption content |
| `conversion_profile_id` | Conversion profile ID |
| `access_control_id` | Access control profile ID |
| `redirect_entry_id` | Redirect target entry ID |
| `recorded_entry_id` | Associated recording entry ID |
| `template_entry_id` | Template entry ID |
| `is_live` | Whether entry is currently live |
| `is_quiz` | Whether entry is a quiz |
| `entitled_kusers_edit` | Users entitled to edit |
| `entitled_kusers_publish` | Users entitled to publish |
| `entitled_kusers_view` | Users entitled to view |

## Caption Field Names (`KalturaESearchCaptionFieldName`)

Use these values in the `fieldName` property of `KalturaESearchCaptionItem`:

| Value | Description |
|-------|-------------|
| `content` | Caption/transcript text content |
| `caption_asset_id` | Caption asset ID |
| `label` | Caption label/display name |
| `language` | Caption language code |
| `start_time` | Caption line start time (use RANGE) |
| `end_time` | Caption line end time (use RANGE) |

## Order-By Field Names (`KalturaESearchEntryOrderByFieldName`)

Use these values in the `sortField` property of `KalturaESearchOrderByItem`:

| Value | Description |
|-------|-------------|
| `created_at` | Creation date |
| `updated_at` | Last update date |
| `name` | Alphabetical by name |
| `plays` | Total play count |
| `plays_last_1_day` | Plays in last 24 hours |
| `plays_last_7_days` | Plays in last 7 days |
| `plays_last_30_days` | Plays in last 30 days |
| `views` | Total view count |
| `views_last_1_day` | Views in last 24 hours |
| `views_last_30_days` | Views in last 30 days |
| `rank` | Relevance/ranking score |
| `start_date` | Scheduling start date |
| `end_date` | Scheduling end date |
| `last_played_at` | Last playback date |

# 10. Error Handling

* Check the HTTP status code first.
* If the status is not 200, parse the JSON error response. Key fields are usually:
    * `code`: A string identifier for the error (e.g., `ESEARCH_SERVICE_DOWN`, `INVALID_KS`).
    * `message`: A human-readable description of the error.
* **Common eSearch Errors:**
    * `ESEARCH_SERVICE_DOWN`: The search service is temporarily unavailable. Consider retrying.
    * `ELASTIC_SEARCH_QUERY_NOT_VALID`: Check the syntax and structure of your `searchParams`.
    * `PERMISSION_READ_ELASTIC_SEARCH_NOT_ALLOWED`: The `ks` used does not have the necessary permissions.
* Implement logging for errors to aid debugging.

**Retry strategy:** For transient errors (HTTP 5xx, `ESEARCH_SERVICE_DOWN`, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`INVALID_KS`, `ELASTIC_SEARCH_QUERY_NOT_VALID`, permission errors), fix the request before retrying — these will not resolve on their own.


# 11. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — Generate the KS required for all eSearch calls
- **[AppTokens](KALTURA_APPTOKENS_API.md)** — Secure KS generation for production integrations
- **[Upload & Delivery](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Upload content that becomes searchable via eSearch
- **[Player Embed](KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed search results for playback
- **[REACH](KALTURA_REACH_API.md)** — Enrichment services: captions, metadata, tagging, and more (improves search quality)
- **[AI Genie](KALTURA_AI_GENIE_API.md)** — Conversational AI search (uses eSearch internally for RAG)
- **[Multi-Stream](KALTURA_MULTI_STREAM_API.md)** — Search for parent entries; use `parentEntryIdEqual` filter to find child entries
- **[Webhooks](KALTURA_WEBHOOKS_API.md)** — Trigger notifications based on content events (search results inform webhook conditions)
- **[Categories & Access Control API](KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md)** — Category-based filtering and entitlements that affect search result visibility
- **[Custom Metadata API](KALTURA_CUSTOM_METADATA_API.md)** — Custom metadata schemas searchable via `KalturaESearchEntryMetadataItem`
- **[Captions & Transcripts API](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md)** — Caption assets searchable via `KalturaESearchCaptionItem`
- **[API Getting Started](KALTURA_API_GETTING_STARTED.md)** — Foundation guide covering content model and API patterns
- **[Syndication](KALTURA_SYNDICATION_API.md)** — Search for entries to include in syndication feeds
- **[Cue Points & Interactive Video](KALTURA_CUE_POINTS_API.md)** — Cue point search with `KalturaESearchCuePointItem` (12 searchable fields: text, tags, question, answers, type)

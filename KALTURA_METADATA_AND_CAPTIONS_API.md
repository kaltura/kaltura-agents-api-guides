# Kaltura Custom Metadata & Captions API

The Custom Metadata & Captions API covers two plugin services: custom metadata schemas and instance data (`metadata_metadataProfile`, `metadata_metadata`), and caption asset management (`caption_captionAsset`). Custom metadata lets you define XSD-based schemas and attach structured XML data to entries, categories, users, or partners. Caption assets let you upload, manage, and serve subtitle files in multiple formats (SRT, DFXP, WebVTT, CAP, SCC).

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))
**Format:** Form-encoded POST, `format=1` for JSON responses
**Services:** `metadata_metadataProfile` (12 actions), `metadata_metadata` (13 actions), `caption_captionAsset` (14 actions)

**Important:** These are plugin services. The service names use underscore-prefixed compound names: `metadata_metadataProfile`, `metadata_metadata`, `caption_captionAsset`.


# 1. Authentication

All endpoints require an ADMIN KS (type=2) with appropriate permissions:

- **Metadata profiles:** `METADATA_PLUGIN_PERMISSION` + `ADMIN_BASE`
- **Metadata CRUD:** `METADATA_PLUGIN_PERMISSION` + `CONTENT_MANAGE_METADATA`
- **Caption assets:** `CAPTION_PLUGIN_PERMISSION` + `CONTENT_MANAGE_BASE`

Generate an ADMIN KS via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

```bash
# Set up environment
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
```


# 2. Metadata Profiles (Schemas)

A `KalturaMetadataProfile` defines a schema (XSD) that describes the structure of custom metadata. You create a profile once, then attach metadata instances conforming to that schema to individual objects (entries, categories, users, etc.).

## 2.1 KalturaMetadataProfile Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Auto-generated profile ID (read-only) |
| `name` | string | Display name |
| `systemName` | string | System-level identifier (machine-friendly) |
| `description` | string | Profile description |
| `status` | integer | `1` = ACTIVE, `2` = DEPRECATED, `3` = TRANSFORMING |
| `metadataObjectType` | integer | Object type this profile applies to (see below) |
| `xsd` | string | The XSD schema definition (read-only on get, set via add/update) |
| `partnerId` | integer | Partner ID (read-only) |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaMetadataProfile"` (read-only) |

## 2.2 Metadata Object Types

| Value | Name | Description |
|-------|------|-------------|
| 1 | ENTRY | Media entries |
| 2 | CATEGORY | Categories |
| 3 | USER | Users |
| 4 | PARTNER | Partner-level (account-wide) |
| 5 | DYNAMIC_OBJECT | Dynamic objects |

## 2.3 Metadata Profile Status Values

| Value | Name | Description |
|-------|------|-------------|
| 1 | ACTIVE | Profile is active and can be used |
| 2 | DEPRECATED | Profile is deprecated |
| 3 | TRANSFORMING | Profile is being transformed (XSD update in progress) |

## 2.4 Create a Metadata Profile (Inline XSD)

```
POST /service/metadata_metadataProfile/action/add
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfile[objectType]=KalturaMetadataProfile" \
  -d "metadataProfile[name]=Content Classification" \
  -d "metadataProfile[metadataObjectType]=1" \
  --data-urlencode 'xsdData=<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="metadata">
    <xsd:complexType>
      <xsd:sequence>
        <xsd:element name="Department" type="xsd:string" minOccurs="0"/>
        <xsd:element name="Project" type="xsd:string" minOccurs="0"/>
        <xsd:element name="Priority" type="xsd:string" minOccurs="0"/>
      </xsd:sequence>
    </xsd:complexType>
  </xsd:element>
</xsd:schema>'
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metadataProfile[objectType]` | string | Yes | Always `KalturaMetadataProfile` |
| `metadataProfile[name]` | string | Yes | Display name for the profile |
| `metadataProfile[systemName]` | string | No | Machine-friendly identifier |
| `metadataProfile[description]` | string | No | Description |
| `metadataProfile[metadataObjectType]` | integer | Yes | `1` = ENTRY, `2` = CATEGORY, `3` = USER, `4` = PARTNER, `5` = DYNAMIC_OBJECT |
| `xsdData` | string | Yes | XSD schema definition (inline) |

**Response:** Full `KalturaMetadataProfile` object with generated `id` and `status=1` (ACTIVE).

## 2.5 Create a Metadata Profile (From File)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/addFromFile" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfile[objectType]=KalturaMetadataProfile" \
  -d "metadataProfile[name]=Content Classification" \
  -d "metadataProfile[metadataObjectType]=1" \
  -F "xsdFile=@schema.xsd"
```

Same as `add`, but the XSD is uploaded as a file instead of inline.

## 2.6 Get a Metadata Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=12345"
```

Returns the full `KalturaMetadataProfile` object. Returns `METADATA_PROFILE_NOT_FOUND` if the profile does not exist.

## 2.7 List Metadata Profiles

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaMetadataProfileFilter" \
  -d "filter[metadataObjectTypeEqual]=1" \
  -d "filter[statusEqual]=1" \
  -d "filter[orderBy]=-createdAt" \
  -d "pager[pageSize]=50"
```

**Filter fields (`KalturaMetadataProfileFilter`):**

| Field | Description |
|-------|-------------|
| `idEqual` | Exact profile ID |
| `idIn` | Comma-separated profile IDs |
| `systemNameEqual` | Exact system name match |
| `metadataObjectTypeEqual` | Filter by object type (1=ENTRY, 2=CATEGORY, etc.) |
| `statusEqual` | Filter by status (1=ACTIVE, 2=DEPRECATED) |
| `nameEqual` | Exact name match |
| `orderBy` | `+createdAt`, `-createdAt`, `+updatedAt`, `-updatedAt` |

**Response:**

```json
{
  "totalCount": 3,
  "objects": [
    {
      "id": 12345,
      "name": "Content Classification",
      "metadataObjectType": 1,
      "status": 1,
      "objectType": "KalturaMetadataProfile"
    }
  ],
  "objectType": "KalturaMetadataProfileListResponse"
}
```

## 2.8 List Fields from Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/listFields" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfileId=12345"
```

Returns a parsed list of field definitions from the XSD. Useful for dynamically building forms or validating metadata XML without parsing XSD yourself.

**Response:**

```json
{
  "totalCount": 3,
  "objects": [
    {
      "fieldName": "Department",
      "objectType": "KalturaMetadataProfileField"
    },
    {
      "fieldName": "Project",
      "objectType": "KalturaMetadataProfileField"
    }
  ],
  "objectType": "KalturaMetadataProfileFieldListResponse"
}
```

## 2.9 Update a Metadata Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=12345" \
  -d "metadataProfile[objectType]=KalturaMetadataProfile" \
  -d "metadataProfile[description]=Updated classification schema"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Profile ID to update |
| `metadataProfile[objectType]` | string | Yes | Always `KalturaMetadataProfile` |
| `metadataProfile[name]` | string | No | Updated name |
| `metadataProfile[description]` | string | No | Updated description |
| `xsdData` | string | No | Updated XSD (triggers re-validation of existing metadata) |

Fields not included remain unchanged. Updating the XSD may cause existing metadata instances to become invalid if they do not conform to the new schema.

**Response:** Full updated `KalturaMetadataProfile` object.

## 2.10 Serve (Raw XSD)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/serve" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=12345"
```

Returns the raw XSD content of the profile. Useful for programmatic schema validation.

## 2.11 Delete a Metadata Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=12345"
```

Deletes the profile and all metadata instances associated with it. This action is irreversible.


# 3. Metadata CRUD

A `KalturaMetadata` instance holds the actual XML data conforming to a metadata profile's XSD schema, attached to a specific object (entry, category, user, etc.).

## 3.1 KalturaMetadata Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Auto-generated metadata ID (read-only) |
| `metadataProfileId` | integer | Profile this metadata conforms to |
| `objectId` | string | ID of the object this metadata is attached to |
| `objectType` | integer | Type of the object (`1` = ENTRY, `2` = CATEGORY, etc.) |
| `status` | integer | `1` = VALID, `2` = INVALID, `3` = DELETED |
| `xml` | string | The metadata XML content |
| `partnerId` | integer | Partner ID (read-only) |
| `version` | integer | Version number, incremented on each update (read-only) |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaMetadata"` (read-only) |

## 3.2 Add Metadata to an Object

```
POST /service/metadata_metadata/action/add
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfileId=12345" \
  -d "objectType=1" \
  -d "objectId=0_abc123" \
  --data-urlencode 'xmlData=<metadata><Department>Engineering</Department><Project>API Guides</Project><Priority>High</Priority></metadata>'
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metadataProfileId` | integer | Yes | Profile ID defining the schema |
| `objectType` | integer | Yes | `1` = ENTRY, `2` = CATEGORY, `3` = USER, `4` = PARTNER, `5` = DYNAMIC_OBJECT |
| `objectId` | string | Yes | ID of the object to attach metadata to |
| `xmlData` | string | Yes | XML data conforming to the profile's XSD |

**Response:** Full `KalturaMetadata` object with generated `id` and `status=1` (VALID).

Each object can have at most one metadata instance per profile. Adding metadata when one already exists for the same profile+object returns an error.

## 3.3 Get Metadata

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=67890"
```

Returns the full `KalturaMetadata` object including the XML content.

## 3.4 List Metadata

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaMetadataFilter" \
  -d "filter[objectIdEqual]=0_abc123" \
  -d "filter[objectTypeEqual]=1" \
  -d "filter[metadataProfileIdEqual]=12345"
```

**Filter fields (`KalturaMetadataFilter`):**

| Field | Description |
|-------|-------------|
| `objectIdEqual` | Exact object ID |
| `objectIdIn` | Comma-separated object IDs |
| `objectTypeEqual` | Object type (1=ENTRY, 2=CATEGORY, etc.) |
| `metadataProfileIdEqual` | Filter by profile ID |
| `metadataProfileIdIn` | Comma-separated profile IDs |
| `statusEqual` | Filter by status (1=VALID, 2=INVALID) |
| `orderBy` | `+createdAt`, `-createdAt`, `+updatedAt`, `-updatedAt`, `+metadataProfileVersion`, `-metadataProfileVersion` |

**Response:**

```json
{
  "totalCount": 1,
  "objects": [
    {
      "id": 67890,
      "metadataProfileId": 12345,
      "objectId": "0_abc123",
      "objectType": 1,
      "status": 1,
      "xml": "<metadata><Department>Engineering</Department><Project>API Guides</Project><Priority>High</Priority></metadata>",
      "objectType": "KalturaMetadata"
    }
  ],
  "objectType": "KalturaMetadataListResponse"
}
```

## 3.5 Update Metadata

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=67890" \
  --data-urlencode 'xmlData=<metadata><Department>Product</Department><Project>API Guides</Project><Priority>Critical</Priority></metadata>'
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Metadata instance ID |
| `xmlData` | string | Yes | Updated XML data conforming to the profile's XSD |

**Response:** Full updated `KalturaMetadata` object with incremented `version`.

## 3.6 Serve (Raw XML)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/serve" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=67890"
```

Returns the raw XML content of the metadata instance. Useful for programmatic XML processing.

## 3.7 Delete Metadata

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=67890"
```

Deletes the metadata instance. Does not affect the metadata profile or the object it was attached to.


# 4. XSD Schema Patterns

## 4.1 Simple Schema with Text, Date, and List Fields

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="metadata">
    <xsd:complexType>
      <xsd:sequence>
        <!-- Free text field -->
        <xsd:element name="Department" type="xsd:string" minOccurs="0"/>

        <!-- Date field (ISO 8601 format) -->
        <xsd:element name="ReviewDate" type="xsd:date" minOccurs="0"/>

        <!-- Integer field -->
        <xsd:element name="ViewCount" type="xsd:int" minOccurs="0"/>

        <!-- Boolean field -->
        <xsd:element name="IsApproved" type="xsd:boolean" minOccurs="0"/>

        <!-- Dropdown / enum field -->
        <xsd:element name="Priority" minOccurs="0">
          <xsd:simpleType>
            <xsd:restriction base="xsd:string">
              <xsd:enumeration value="Low"/>
              <xsd:enumeration value="Medium"/>
              <xsd:enumeration value="High"/>
              <xsd:enumeration value="Critical"/>
            </xsd:restriction>
          </xsd:simpleType>
        </xsd:element>

        <!-- Multi-value (repeatable) field -->
        <xsd:element name="Tag" type="xsd:string" minOccurs="0" maxOccurs="unbounded"/>
      </xsd:sequence>
    </xsd:complexType>
  </xsd:element>
</xsd:schema>
```

## 4.2 Corresponding XML Data

```xml
<metadata>
  <Department>Engineering</Department>
  <ReviewDate>2025-06-15</ReviewDate>
  <ViewCount>42</ViewCount>
  <IsApproved>true</IsApproved>
  <Priority>High</Priority>
  <Tag>api</Tag>
  <Tag>documentation</Tag>
  <Tag>v3</Tag>
</metadata>
```

## 4.3 Field Type Reference

| XSD Type | Description | Example Value |
|----------|-------------|---------------|
| `xsd:string` | Free text | `"Engineering"` |
| `xsd:int` | Integer | `42` |
| `xsd:date` | ISO 8601 date | `"2025-06-15"` |
| `xsd:dateTime` | ISO 8601 datetime | `"2025-06-15T10:30:00Z"` |
| `xsd:boolean` | Boolean | `"true"` or `"false"` |
| `xsd:float` | Decimal number | `"3.14"` |
| Enumeration | Restricted list of values | Defined via `xsd:restriction` |

Use `minOccurs="0"` to make fields optional. Use `maxOccurs="unbounded"` for repeatable (multi-value) fields.


# 5. Caption Assets

A `KalturaCaptionAsset` represents a subtitle or caption file attached to a media entry. Caption creation is a two-step process: first create the asset metadata (`captionAsset.add`), then upload the content (`captionAsset.setContent`).

## 5.1 KalturaCaptionAsset Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-generated asset ID (read-only) |
| `entryId` | string | Media entry this caption belongs to |
| `label` | string | Display label (e.g., "English", "Spanish CC") |
| `language` | string | Language code from KalturaLanguage enum (e.g., `"English"`, `"Spanish"`) |
| `format` | integer | Caption format (see below) |
| `status` | integer | Asset status (see below) |
| `isDefault` | boolean | Whether this is the default caption for the entry |
| `accuracy` | integer | Accuracy percentage (for auto-generated captions) |
| `partnerId` | integer | Partner ID (read-only) |
| `size` | integer | File size in bytes (read-only) |
| `version` | integer | Version number (read-only) |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaCaptionAsset"` (read-only) |

## 5.2 Caption Formats

| Value | Name | Description |
|-------|------|-------------|
| 1 | SRT | SubRip subtitle format |
| 2 | DFXP | Distribution Format Exchange Profile (TTML) |
| 3 | WEBVTT | Web Video Text Tracks |
| 4 | CAP | Cheetah CAP |
| 5 | SCC | Scenarist Closed Captions |

## 5.3 Caption Asset Status Values

| Value | Name | Description |
|-------|------|-------------|
| -1 | ERROR | Processing error |
| 0 | QUEUED | Queued for processing |
| 2 | READY | Ready for use |
| 3 | DELETED | Soft-deleted |
| 7 | IMPORTING | Being imported |

## 5.4 Caption Languages

Use the KalturaLanguage enum values, which are human-readable language names: `"English"`, `"Spanish"`, `"French"`, `"German"`, `"Japanese"`, `"Chinese"`, `"Arabic"`, `"Portuguese"`, `"Russian"`, `"Korean"`, `"Italian"`, `"Dutch"`, `"Hebrew"`, `"Hindi"`, etc.

## 5.5 Create a Caption Asset

```
POST /service/caption_captionAsset/action/add
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=0_abc123" \
  -d "captionAsset[objectType]=KalturaCaptionAsset" \
  -d "captionAsset[label]=English" \
  -d "captionAsset[language]=English" \
  -d "captionAsset[format]=1" \
  -d "captionAsset[isDefault]=1"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entryId` | string | Yes | Media entry ID |
| `captionAsset[objectType]` | string | Yes | Always `KalturaCaptionAsset` |
| `captionAsset[label]` | string | No | Display label |
| `captionAsset[language]` | string | Yes | Language (KalturaLanguage enum value) |
| `captionAsset[format]` | integer | Yes | `1`=SRT, `2`=DFXP, `3`=WEBVTT, `4`=CAP, `5`=SCC |
| `captionAsset[isDefault]` | boolean | No | Set as default caption |

**Response:** `KalturaCaptionAsset` object with generated `id` and `status=0` (QUEUED).

## 5.6 Set Caption Content

After creating the asset, upload the caption content:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/setContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=1_caption_id" \
  -d "contentResource[objectType]=KalturaStringResource" \
  --data-urlencode 'contentResource[content]=1
00:00:00,000 --> 00:00:05,000
Welcome to the presentation.

2
00:00:05,000 --> 00:00:10,000
Today we will cover the Kaltura API.'
```

For file uploads, use `KalturaUploadedFileTokenResource` with an upload token (see [Upload & Delivery API](KALTURA_UPLOAD_AND_DELIVERY_API.md)):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/setContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=1_caption_id" \
  -d "contentResource[objectType]=KalturaUploadedFileTokenResource" \
  -d "contentResource[token]=upload_token_id"
```

**Response:** Updated `KalturaCaptionAsset` object. Status transitions to `2` (READY) after processing.

## 5.7 Get a Caption Asset

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionAssetId=1_caption_id"
```

## 5.8 List Caption Assets

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaAssetFilter" \
  -d "filter[entryIdEqual]=0_abc123"
```

**Filter fields (`KalturaAssetFilter`):**

| Field | Description |
|-------|-------------|
| `entryIdEqual` | Filter by entry ID |
| `entryIdIn` | Comma-separated entry IDs |
| `statusEqual` | Filter by status |
| `statusIn` | Comma-separated status values |
| `formatEqual` | Filter by caption format |

**Response:**

```json
{
  "totalCount": 2,
  "objects": [
    {
      "id": "1_abc123",
      "entryId": "0_abc123",
      "label": "English",
      "language": "English",
      "format": 1,
      "status": 2,
      "isDefault": true,
      "objectType": "KalturaCaptionAsset"
    }
  ],
  "objectType": "KalturaCaptionAssetListResponse"
}
```

## 5.9 Update a Caption Asset

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=1_caption_id" \
  -d "captionAsset[objectType]=KalturaCaptionAsset" \
  -d "captionAsset[label]=English (Updated)"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Caption asset ID |
| `captionAsset[objectType]` | string | Yes | Always `KalturaCaptionAsset` |
| `captionAsset[label]` | string | No | Updated label |
| `captionAsset[language]` | string | No | Updated language |
| `captionAsset[isDefault]` | boolean | No | Update default status |

## 5.10 Set as Default Caption

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/setAsDefault" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionAssetId=1_caption_id"
```

Marks this caption asset as the default for its entry. Unsets the previous default automatically.

## 5.11 Delete a Caption Asset

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionAssetId=1_caption_id"
```


# 6. Serving Captions

## 6.1 Serve Raw Caption File

Returns the caption content in its original format (SRT, DFXP, etc.):

```bash
curl "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/serve?ks=$KALTURA_KS&captionAssetId=1_caption_id"
```

This is a GET request that returns raw text content, not JSON. The response Content-Type matches the caption format.

## 6.2 Serve as WebVTT

Converts any caption format to WebVTT on the fly:

```bash
curl "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/serveWebVTT?ks=$KALTURA_KS&captionAssetId=1_caption_id"
```

Returns raw WebVTT text content. Useful for HTML5 video players that require WebVTT format.

## 6.3 Serve as JSON

Returns the caption data as structured JSON:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/serveAsJson" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionAssetId=1_caption_id"
```

## 6.4 Get Download URL

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/getUrl" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=1_caption_id"
```

Returns a direct download URL string for the caption file.


# 7. Common Integration Patterns

## 7.1 Upload SRT Captions to an Entry

```bash
# Step 1: Create the caption asset
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$ENTRY_ID" \
  -d "captionAsset[objectType]=KalturaCaptionAsset" \
  -d "captionAsset[label]=English" \
  -d "captionAsset[language]=English" \
  -d "captionAsset[format]=1"

# Step 2: Upload the content (using string resource for small captions)
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/setContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CAPTION_ASSET_ID" \
  -d "contentResource[objectType]=KalturaStringResource" \
  --data-urlencode "contentResource[content]@captions.srt"

# Step 3: Set as default
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/setAsDefault" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionAssetId=$CAPTION_ASSET_ID"
```

## 7.2 Define Metadata Schema, Attach Data, Search via eSearch

```bash
# Step 1: Create a metadata profile
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfile[objectType]=KalturaMetadataProfile" \
  -d "metadataProfile[name]=Project Tracking" \
  -d "metadataProfile[metadataObjectType]=1" \
  --data-urlencode 'xsdData=<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="metadata">
    <xsd:complexType>
      <xsd:sequence>
        <xsd:element name="ProjectName" type="xsd:string" minOccurs="0"/>
        <xsd:element name="Status" type="xsd:string" minOccurs="0"/>
      </xsd:sequence>
    </xsd:complexType>
  </xsd:element>
</xsd:schema>'

# Step 2: Attach metadata to an entry
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfileId=$PROFILE_ID" \
  -d "objectType=1" \
  -d "objectId=$ENTRY_ID" \
  --data-urlencode 'xmlData=<metadata><ProjectName>API Guides</ProjectName><Status>Active</Status></metadata>'

# Step 3: Search entries by metadata via eSearch (see eSearch API guide)
curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "searchParams[objectType]=KalturaESearchEntryParams" \
  -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
  -d "searchParams[searchOperator][operator]=1" \
  -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchEntryMetadataItem" \
  -d "searchParams[searchOperator][searchItems][0][searchTerm]=API Guides" \
  -d "searchParams[searchOperator][searchItems][0][itemType]=1" \
  -d "searchParams[searchOperator][searchItems][0][metadataProfileId]=$PROFILE_ID"
```


# 8. Error Handling

| Error Code | Meaning |
|------------|---------|
| `METADATA_PROFILE_NOT_FOUND` | Metadata profile ID not found |
| `METADATA_NOT_FOUND` | Metadata instance ID not found |
| `INVALID_METADATA_PROFILE_SCHEMA` | XSD schema is invalid |
| `METADATA_ALREADY_EXISTS` | Metadata already exists for this profile+object combination |
| `INVALID_METADATA_DATA` | XML data does not conform to the profile's XSD schema |
| `INVALID_OBJECT_ID` | The object ID does not exist |
| `CAPTION_ASSET_ID_NOT_FOUND` | Caption asset ID not found |
| `ENTRY_ID_NOT_FOUND` | Entry ID not found when creating a caption asset |
| `INVALID_ENTRY_ID` | Invalid entry ID format |
| `CAPTION_ASSET_IS_NOT_READY` | Caption asset is not in READY status (cannot serve) |
| `FLAVOR_ASSET_ID_NOT_FOUND` | Asset not found (generic asset error) |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (HTTP 400, `METADATA_PROFILE_NOT_FOUND`, `ENTRY_ID_NOT_FOUND`), fix the request before retrying.


# 9. Best Practices

- **Use systemName for machine references.** Set `systemName` on metadata profiles for stable lookups. Display names may change; system names provide a reliable key for code.
- **Keep XSD schemas simple.** Use `xsd:string` for most fields. Only use typed fields (`xsd:int`, `xsd:date`) when you need server-side validation. Simpler schemas are easier to maintain and less likely to break existing metadata.
- **One profile per use case.** Create separate metadata profiles for different purposes (e.g., "Content Classification", "Workflow Status", "SEO Tags") rather than one large profile. This makes it easier to manage permissions and lifecycle independently.
- **Use eSearch for metadata queries.** Do not use `metadata.list` to find entries by metadata values. Use `KalturaESearchEntryMetadataItem` in eSearch for efficient cross-field searching. See [eSearch API](KALTURA_ESEARCH_API.md).
- **Two-step caption creation.** Always create the asset first (`captionAsset.add`), then upload content (`captionAsset.setContent`). This ensures the asset metadata (language, format, label) is set before content processing begins.
- **Use KalturaStringResource for small captions.** For caption files under ~1 MB, `KalturaStringResource` with inline content is simpler than the upload token flow. For larger files, use `KalturaUploadedFileTokenResource` with an upload token.
- **Set one default caption per entry.** Use `captionAsset.setAsDefault` after uploading. The player uses the default caption for auto-display. Only one caption can be default per entry.
- **Use serveWebVTT for player integration.** When building custom players, `serveWebVTT` converts any source format (SRT, DFXP, etc.) to WebVTT on the fly, which is the standard format for HTML5 `<track>` elements.
- **Search captions via eSearch.** Use `KalturaESearchCaptionItem` in eSearch to search within caption text across entries. See [eSearch API](KALTURA_ESEARCH_API.md).


# 10. Related Guides

- **[REACH API](KALTURA_REACH_API.md)** — AI-generated captions (this guide covers manual caption management)
- **[Agents Manager API](KALTURA_AGENTS_MANAGER_API.md)** — Automated metadata enrichment via AI agents
- **[eSearch API](KALTURA_ESEARCH_API.md)** — Search metadata (`KalturaESearchEntryMetadataItem`) and captions (`KalturaESearchCaptionItem`)
- **[Webhooks API](KALTURA_WEBHOOKS_API.md)** — Metadata change events and caption processing notifications
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Captions displayed in the Kaltura Player
- **[Upload & Delivery API](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Content resources for `setContent` (upload tokens, URL resources)
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and permission scoping
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure auth without admin secrets

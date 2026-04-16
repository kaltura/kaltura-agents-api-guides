# Kaltura Custom Metadata API

The Custom Metadata API lets you define XSD-based schemas (metadata profiles) and attach structured XML data to entries, categories, users, partners, or user-entry records. Schemas support typed fields with annotations that control KMC rendering, eSearch indexing, and UI behavior. An optional XSLT pipeline transforms metadata on every add/update.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)  
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** Form-encoded POST, `format=1` for JSON responses  
**Services:** `metadata_metadataProfile` (10 actions), `metadata_metadata` (9 actions)  

**Important:** These are plugin services. The service names use underscore-prefixed compound names: `metadata_metadataProfile`, `metadata_metadata`.  


# 1. Authentication

All endpoints require an ADMIN KS (type=2) with appropriate permissions:

- **Metadata profiles:** `METADATA_PLUGIN_PERMISSION` + `ADMIN_BASE`
- **Metadata CRUD:** `METADATA_PLUGIN_PERMISSION` + `CONTENT_MANAGE_METADATA`

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
| `partnerId` | integer | Partner ID (read-only) |
| `name` | string | Display name |
| `systemName` | string | System-level identifier (machine-friendly, use for stable lookups) |
| `description` | string | Profile description |
| `status` | integer | `1` = ACTIVE, `2` = DEPRECATED, `3` = TRANSFORMING |
| `metadataObjectType` | integer | Object type this profile applies to (see 2.2) |
| `version` | integer | Profile version, incremented on XSD changes (read-only, filterable) |
| `xsd` | string | The XSD schema definition (read-only on get, set via add/update) |
| `xslt` | string | XSLT applied on every metadata add/update (read-only, set via `updateTransformationFromFile`) |
| `createMode` | integer | `1` = API, `2` = KMC, `3` = APP. KMC hides API-created profiles by default. |
| `disableReIndexing` | boolean | When true, prevents re-indexing of related objects on metadata changes |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaMetadataProfile"` (read-only) |

## 2.2 Metadata Object Types

| Value | Name | Description |
|-------|------|-------------|
| 1 | ENTRY | Media entries |
| 2 | CATEGORY | Categories |
| 3 | USER | Users |
| 4 | PARTNER | Partner-level (account-wide configuration) |
| 5 | DYNAMIC_OBJECT | Dynamic objects |
| 6 | USER_ENTRY | Per-user-per-entry records (quiz answers, watch progress) |

## 2.3 Profile Status Values

| Value | Name | Description |
|-------|------|-------------|
| 1 | ACTIVE | Profile is active and can be used |
| 2 | DEPRECATED | Profile is deprecated |
| 3 | TRANSFORMING | Profile XSD update in progress, re-validating existing metadata |

## 2.4 Create Profile (Inline XSD)

```
POST /service/metadata_metadataProfile/action/add
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfile[objectType]=KalturaMetadataProfile" \
  -d "metadataProfile[name]=Content Classification" \
  -d "metadataProfile[systemName]=content_classification" \
  -d "metadataProfile[description]=Classify content by department and priority" \
  -d "metadataProfile[metadataObjectType]=1" \
  --data-urlencode 'xsdData=<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="metadata">
    <xsd:complexType>
      <xsd:sequence>
        <xsd:element name="Department" minOccurs="0" maxOccurs="1">
          <xsd:annotation><xsd:appinfo>
            <label>Department</label>
            <key>department</key>
            <searchable>true</searchable>
            <description>Owning department</description>
          </xsd:appinfo></xsd:annotation>
          <xsd:simpleType>
            <xsd:restriction base="listType">
              <xsd:enumeration value="Engineering"/>
              <xsd:enumeration value="Marketing"/>
              <xsd:enumeration value="Sales"/>
              <xsd:enumeration value="Support"/>
            </xsd:restriction>
          </xsd:simpleType>
        </xsd:element>
        <xsd:element name="Project" type="textType" minOccurs="0" maxOccurs="1">
          <xsd:annotation><xsd:appinfo>
            <label>Project Name</label>
            <key>project</key>
            <searchable>true</searchable>
          </xsd:appinfo></xsd:annotation>
        </xsd:element>
      </xsd:sequence>
    </xsd:complexType>
  </xsd:element>
  <xsd:complexType name="textType">
    <xsd:simpleContent>
      <xsd:extension base="xsd:string"/>
    </xsd:simpleContent>
  </xsd:complexType>
  <xsd:complexType name="dateType">
    <xsd:simpleContent>
      <xsd:extension base="xsd:long"/>
    </xsd:simpleContent>
  </xsd:complexType>
  <xsd:complexType name="objectType">
    <xsd:simpleContent>
      <xsd:extension base="xsd:string"/>
    </xsd:simpleContent>
  </xsd:complexType>
  <xsd:simpleType name="listType">
    <xsd:restriction base="xsd:string"/>
  </xsd:simpleType>
</xsd:schema>'
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metadataProfile[objectType]` | string | Yes | Always `KalturaMetadataProfile` |
| `metadataProfile[name]` | string | Yes | Display name for the profile |
| `metadataProfile[systemName]` | string | No | Machine-friendly identifier for stable lookups |
| `metadataProfile[description]` | string | No | Description |
| `metadataProfile[metadataObjectType]` | integer | Yes | `1`=ENTRY, `2`=CATEGORY, `3`=USER, `4`=PARTNER, `5`=DYNAMIC_OBJECT, `6`=USER_ENTRY |
| `xsdData` | string | Yes | XSD schema definition (inline, URL-encoded) |

**Response:** Full `KalturaMetadataProfile` object with generated `id`, `version=1`, and `status=1` (ACTIVE).

## 2.5 Create Profile (File Upload)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/addFromFile" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfile[objectType]=KalturaMetadataProfile" \
  -d "metadataProfile[name]=Content Classification" \
  -d "metadataProfile[systemName]=content_classification" \
  -d "metadataProfile[metadataObjectType]=1" \
  -F "xsdFile=@schema.xsd"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metadataProfile[objectType]` | string | Yes | Always `KalturaMetadataProfile` |
| `metadataProfile[name]` | string | Yes | Display name for the profile |
| `metadataProfile[systemName]` | string | No | Machine-friendly identifier for stable lookups |
| `metadataProfile[metadataObjectType]` | integer | Yes | `1`=ENTRY, `2`=CATEGORY, `3`=USER, `4`=PARTNER, `5`=DYNAMIC_OBJECT, `6`=USER_ENTRY |
| `xsdFile` | file | Yes | XSD schema file upload (multipart form field) |

Same as `add`, but the XSD is uploaded as a file instead of inline.

**Response:** Full `KalturaMetadataProfile` object with generated `id`, `version=1`, and `status=1` (ACTIVE).

## 2.6 Get Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$PROFILE_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Profile ID to retrieve |

Returns the full `KalturaMetadataProfile` object including the XSD content. Returns `METADATA_PROFILE_NOT_FOUND` if the profile does not exist.

**Response:**

```json
{
  "id": 12345,
  "partnerId": 123456,
  "name": "Content Classification",
  "systemName": "content_classification",
  "description": "Classify content by department and priority",
  "status": 1,
  "metadataObjectType": 1,
  "version": 1,
  "createMode": 1,
  "xsd": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><xsd:schema ...>...</xsd:schema>",
  "createdAt": 1718409600,
  "updatedAt": 1718409600,
  "objectType": "KalturaMetadataProfile"
}
```

## 2.7 List Profiles

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaMetadataProfileFilter" \
  -d "filter[systemNameEqual]=content_classification" \
  -d "filter[statusEqual]=1" \
  -d "filter[orderBy]=-createdAt" \
  -d "pager[pageSize]=50"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filter[objectType]` | string | Yes | Always `KalturaMetadataProfileFilter` |
| `filter[...]` | various | No | Filter fields (see table below) |
| `pager[pageSize]` | integer | No | Results per page (default 30, max 500) |
| `pager[pageIndex]` | integer | No | Page number, 1-based (default 1) |

**Filter fields (`KalturaMetadataProfileFilter`):**

| Field | Description |
|-------|-------------|
| `idEqual` / `idIn` | Exact profile ID or comma-separated IDs |
| `nameEqual` | Exact name match |
| `systemNameEqual` / `systemNameIn` | Exact system name or comma-separated system names |
| `metadataObjectTypeEqual` / `metadataObjectTypeIn` | Filter by object type (1=ENTRY, etc.) |
| `statusEqual` / `statusIn` | Filter by status (1=ACTIVE, 2=DEPRECATED, 3=TRANSFORMING) |
| `versionEqual` | Filter by profile version |
| `createModeEqual` / `createModeNotEqual` / `createModeIn` / `createModeNotIn` | Filter by creation mode (1=API, 2=KMC, 3=APP) |
| `createdAtGreaterThanOrEqual` / `createdAtLessThanOrEqual` | Date range filters (Unix timestamp) |
| `updatedAtGreaterThanOrEqual` / `updatedAtLessThanOrEqual` | Date range filters (Unix timestamp) |
| `orderBy` | `+createdAt`, `-createdAt`, `+updatedAt`, `-updatedAt` |

**Response:**

```json
{
  "totalCount": 1,
  "objects": [
    {
      "id": 12345,
      "name": "Content Classification",
      "systemName": "content_classification",
      "metadataObjectType": 1,
      "status": 1,
      "version": 1,
      "createMode": 1,
      "objectType": "KalturaMetadataProfile"
    }
  ],
  "objectType": "KalturaMetadataProfileListResponse"
}
```

## 2.8 List Fields

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/listFields" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfileId=$PROFILE_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metadataProfileId` | integer | Yes | Profile ID whose XSD fields to list |

Returns a parsed list of field definitions from the XSD. Useful for dynamically building forms or validating metadata XML without parsing XSD yourself.

**Response:**

```json
{
  "totalCount": 2,
  "objects": [
    {"fieldName": "Department", "objectType": "KalturaMetadataProfileField"},
    {"fieldName": "Project", "objectType": "KalturaMetadataProfileField"}
  ],
  "objectType": "KalturaMetadataProfileFieldListResponse"
}
```

## 2.9 Update Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$PROFILE_ID" \
  -d "metadataProfile[objectType]=KalturaMetadataProfile" \
  -d "metadataProfile[description]=Updated classification schema"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Profile ID to update |
| `metadataProfile[objectType]` | string | Yes | Always `KalturaMetadataProfile` |
| `metadataProfile[name]` | string | No | Updated name |
| `metadataProfile[description]` | string | No | Updated description |
| `xsdData` | string | No | Updated XSD (triggers re-validation of existing metadata, increments version) |

Fields not included remain unchanged. Updating the XSD triggers the server to re-validate all existing metadata instances against the new schema. Incompatible changes cause `METADATA_UNABLE_TO_TRANSFORM`.

## 2.10 Update XSD from File

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/updateDefinitionFromFile" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$PROFILE_ID" \
  -F "xsdFile=@updated_schema.xsd"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Profile ID to update |
| `xsdFile` | file | Yes | Updated XSD schema file (multipart form field) |

Updates the profile XSD from a file upload. Triggers re-validation and transformation of all existing metadata instances. The profile `version` is incremented. During transformation, the profile status transitions to `TRANSFORMING` (3) and returns to `ACTIVE` (1) when complete.

## 2.11 Revert Profile Version

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/revert" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$PROFILE_ID" \
  -d "toVersion=2"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Profile ID |
| `toVersion` | integer | Yes | Version number to revert to |

Reverts the profile XSD to a previous version. All metadata instances are also reverted and re-validated against the restored schema. The `version` field is incremented (revert creates a new version, not a rollback).

## 2.12 Serve XSD

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/serve" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$PROFILE_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Profile ID whose XSD to serve |

Returns the raw XSD content of the profile. Useful for programmatic schema validation or building dynamic forms from the schema definition.

## 2.13 Delete Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$PROFILE_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Profile ID to delete |

Deletes the profile and cascades to all metadata instances associated with it. This action is irreversible. Profiles of type `DYNAMIC_OBJECT` with active references return `METADATA_PROFILE_REFERENCE_EXISTS`.


# 3. XSD Schema Design

Every Kaltura metadata XSD must include four base type definitions that the KMC and eSearch use for field type detection. Fields annotated with `<appinfo>` elements control how the KMC renders the metadata form and how eSearch indexes the values.

## 3.1 Kaltura-Native Field Types

| KMC Type | XSD Type | Storage | KMC Control | eSearch Behavior |
|----------|----------|---------|-------------|------------------|
| Text | `textType` | String | TextArea (single) / Textbox (multi) | Full-text search |
| Date | `dateType` | Unix timestamp (long) | DatePicker | Range queries |
| Entry Link | `objectType` | Entry/object ID string | LinkedEntries selector | ID match |
| Dropdown | `listType` + `enumeration` | String | Dropdown (single) / List (multi) | Exact match, KMC filter column |

**Date fields store Unix timestamps as longs (e.g., `1718409600` for 2024-06-15), not ISO date strings.** This is the Kaltura-native convention used by KMC-NG for DatePicker rendering and eSearch range queries.

## 3.2 Base Type Definitions (Required)

Every Kaltura XSD must include these four type definitions at the bottom of the schema. Without them, the KMC cannot determine field types for form rendering:

```xml
<xsd:complexType name="textType">
  <xsd:simpleContent>
    <xsd:extension base="xsd:string"/>
  </xsd:simpleContent>
</xsd:complexType>
<xsd:complexType name="dateType">
  <xsd:simpleContent>
    <xsd:extension base="xsd:long"/>
  </xsd:simpleContent>
</xsd:complexType>
<xsd:complexType name="objectType">
  <xsd:simpleContent>
    <xsd:extension base="xsd:string"/>
  </xsd:simpleContent>
</xsd:complexType>
<xsd:simpleType name="listType">
  <xsd:restriction base="xsd:string"/>
</xsd:simpleType>
```

## 3.3 Field Annotations (`<appinfo>`)

Annotations control how the KMC-NG renders each field and how eSearch indexes it:

```xml
<xsd:element name="Department" minOccurs="0">
  <xsd:annotation>
    <xsd:appinfo>
      <label>Department</label>
      <key>department</key>
      <searchable>true</searchable>
      <description>Owning department for this content</description>
      <hidden>false</hidden>
      <timeControl>false</timeControl>
    </xsd:appinfo>
  </xsd:annotation>
  <!-- field type definition follows -->
</xsd:element>
```

| Annotation | Purpose | Default |
|-----------|---------|---------|
| `<label>` | Display name shown in KMC metadata form | Element name |
| `<key>` | Programmatic identifier used in custom integrations | Element name |
| `<searchable>` | When `true`, field is indexed in eSearch | `false` |
| `<description>` | Help text shown below the field in KMC | None |
| `<hidden>` | When `true`, field is hidden from KMC UI (for computed/internal fields) | `false` |
| `<timeControl>` | When `true`, enables time-based metadata entry (chapter markers in video timeline) | `false` |

Applications building custom metadata forms read these annotations from the XSD (via `metadataProfile.get` or `metadataProfile.serve`) to auto-generate UI controls matching the KMC behavior.

## 3.4 Enum Fields (Dropdown)

Use `listType` with `xsd:enumeration` restrictions to create dropdown fields. This is the only field type available as a KMC filter column:

```xml
<xsd:element name="Priority" minOccurs="0">
  <xsd:annotation><xsd:appinfo>
    <label>Priority</label>
    <key>priority</key>
    <searchable>true</searchable>
  </xsd:appinfo></xsd:annotation>
  <xsd:simpleType>
    <xsd:restriction base="listType">
      <xsd:enumeration value="Low"/>
      <xsd:enumeration value="Medium"/>
      <xsd:enumeration value="High"/>
      <xsd:enumeration value="Critical"/>
    </xsd:restriction>
  </xsd:simpleType>
</xsd:element>
```

## 3.5 Multi-Value Fields

Use `maxOccurs="unbounded"` for repeatable fields:

```xml
<xsd:element name="Tag" type="textType" minOccurs="0" maxOccurs="unbounded">
  <xsd:annotation><xsd:appinfo>
    <label>Tags</label>
    <key>tags</key>
    <searchable>true</searchable>
  </xsd:appinfo></xsd:annotation>
</xsd:element>
```

In metadata XML, each value is a separate element:

```xml
<metadata>
  <Tag>api</Tag>
  <Tag>documentation</Tag>
  <Tag>v3</Tag>
</metadata>
```

## 3.6 Required vs Optional Fields

- `minOccurs="0"` — optional field (recommended for most fields)
- `minOccurs="1"` — required field (metadata XML must include this element)
- `maxOccurs="1"` — single value (default)
- `maxOccurs="unbounded"` — multi-value (repeatable)

## 3.7 Nested Elements

Use `complexType` with `sequence` for grouped fields:

```xml
<xsd:element name="ReviewInfo" minOccurs="0">
  <xsd:complexType>
    <xsd:sequence>
      <xsd:element name="ReviewedBy" type="textType" minOccurs="0"/>
      <xsd:element name="ReviewDate" type="dateType" minOccurs="0"/>
      <xsd:element name="ReviewStatus" minOccurs="0">
        <xsd:simpleType>
          <xsd:restriction base="listType">
            <xsd:enumeration value="Pending"/>
            <xsd:enumeration value="Approved"/>
            <xsd:enumeration value="Rejected"/>
          </xsd:restriction>
        </xsd:simpleType>
      </xsd:element>
    </xsd:sequence>
  </xsd:complexType>
</xsd:element>
```

## 3.8 Complete Schema Example

A production-ready schema with all field types, annotations, and required base type definitions:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="metadata">
    <xsd:complexType>
      <xsd:sequence>

        <xsd:element name="Department" minOccurs="0">
          <xsd:annotation><xsd:appinfo>
            <label>Department</label>
            <key>department</key>
            <searchable>true</searchable>
            <description>Owning department</description>
          </xsd:appinfo></xsd:annotation>
          <xsd:simpleType>
            <xsd:restriction base="listType">
              <xsd:enumeration value="Engineering"/>
              <xsd:enumeration value="Marketing"/>
              <xsd:enumeration value="Sales"/>
            </xsd:restriction>
          </xsd:simpleType>
        </xsd:element>

        <xsd:element name="ProjectName" type="textType" minOccurs="0">
          <xsd:annotation><xsd:appinfo>
            <label>Project Name</label>
            <key>project_name</key>
            <searchable>true</searchable>
          </xsd:appinfo></xsd:annotation>
        </xsd:element>

        <xsd:element name="DueDate" type="dateType" minOccurs="0">
          <xsd:annotation><xsd:appinfo>
            <label>Due Date</label>
            <key>due_date</key>
            <searchable>true</searchable>
          </xsd:appinfo></xsd:annotation>
        </xsd:element>

        <xsd:element name="RelatedEntry" type="objectType" minOccurs="0">
          <xsd:annotation><xsd:appinfo>
            <label>Related Entry</label>
            <key>related_entry</key>
            <searchable>true</searchable>
          </xsd:appinfo></xsd:annotation>
        </xsd:element>

        <xsd:element name="Tag" type="textType" minOccurs="0" maxOccurs="unbounded">
          <xsd:annotation><xsd:appinfo>
            <label>Tags</label>
            <key>tags</key>
            <searchable>true</searchable>
          </xsd:appinfo></xsd:annotation>
        </xsd:element>

        <xsd:element name="InternalNotes" type="textType" minOccurs="0">
          <xsd:annotation><xsd:appinfo>
            <label>Internal Notes</label>
            <key>internal_notes</key>
            <searchable>false</searchable>
            <hidden>true</hidden>
          </xsd:appinfo></xsd:annotation>
        </xsd:element>

      </xsd:sequence>
    </xsd:complexType>
  </xsd:element>

  <!-- Required base type definitions for KMC compatibility -->
  <xsd:complexType name="textType">
    <xsd:simpleContent>
      <xsd:extension base="xsd:string"/>
    </xsd:simpleContent>
  </xsd:complexType>
  <xsd:complexType name="dateType">
    <xsd:simpleContent>
      <xsd:extension base="xsd:long"/>
    </xsd:simpleContent>
  </xsd:complexType>
  <xsd:complexType name="objectType">
    <xsd:simpleContent>
      <xsd:extension base="xsd:string"/>
    </xsd:simpleContent>
  </xsd:complexType>
  <xsd:simpleType name="listType">
    <xsd:restriction base="xsd:string"/>
  </xsd:simpleType>
</xsd:schema>
```

## 3.9 Field Type Reference

| KMC Type | XSD Pattern | Example Value | KMC Single Control | KMC Multi Control |
|----------|------------|---------------|--------------------|--------------------|
| Text | `type="textType"` | `"API Guides"` | TextAreaControl | TextboxControl |
| Date | `type="dateType"` | `1718409600` (Unix ts) | DatePickerControl | DatePickerControl |
| Entry Link | `type="objectType"` | `"0_abc123"` | LinkedEntriesControl | LinkedEntriesControl |
| Dropdown | `base="listType"` + `enumeration` | `"Engineering"` | DynamicDropdownControl | ListControl |
| Nested | `complexType` + `sequence` | (sub-elements) | DynamicSectionControl | — |


# 4. Metadata Instances (CRUD)

A `KalturaMetadata` instance holds the actual XML data conforming to a metadata profile's XSD schema, attached to a specific object. Each object can have at most one metadata instance per profile.

## 4.1 KalturaMetadata Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Auto-generated metadata ID (read-only) |
| `metadataProfileId` | integer | Profile this metadata conforms to |
| `metadataProfileVersion` | integer | Profile version this metadata was validated against (read-only, filterable) |
| `objectId` | string | ID of the object this metadata is attached to |
| `objectType` | integer | Type of the object (1=ENTRY, 2=CATEGORY, etc.) |
| `status` | integer | `1` = VALID, `2` = INVALID, `3` = DELETED |
| `xml` | string | The metadata XML content |
| `version` | integer | Version number, incremented on each update (read-only) |
| `partnerId` | integer | Partner ID (read-only) |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaMetadata"` (read-only) |

## 4.2 Metadata Status Values

| Value | Name | Description |
|-------|------|-------------|
| 1 | VALID | Metadata XML conforms to its profile XSD |
| 2 | INVALID | Metadata XML failed validation (after XSD change) |
| 3 | DELETED | Soft-deleted |

## 4.3 Add Metadata (Inline XML)

```
POST /service/metadata_metadata/action/add
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfileId=$PROFILE_ID" \
  -d "objectType=1" \
  -d "objectId=$ENTRY_ID" \
  --data-urlencode 'xmlData=<metadata><Department>Engineering</Department><ProjectName>API Guides</ProjectName><DueDate>1718409600</DueDate><Tag>api</Tag><Tag>docs</Tag></metadata>'
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metadataProfileId` | integer | Yes | Profile ID defining the schema |
| `objectType` | integer | Yes | `1`=ENTRY, `2`=CATEGORY, `3`=USER, `4`=PARTNER, `5`=DYNAMIC_OBJECT, `6`=USER_ENTRY |
| `objectId` | string | Yes | ID of the object to attach metadata to |
| `xmlData` | string | Yes | XML data conforming to the profile's XSD |

**Important:** XML field order must match the `<xsd:sequence>` order defined in the profile's XSD. Out-of-order fields cause validation errors. Field names are case-sensitive.

**Response:**

```json
{
  "id": 67890,
  "partnerId": 123456,
  "metadataProfileId": 12345,
  "metadataProfileVersion": 1,
  "metadataObjectType": 1,
  "objectId": "0_abc123",
  "objectType": "KalturaMetadata",
  "status": 1,
  "version": 1,
  "xml": "<metadata><Department>Engineering</Department><ProjectName>API Guides</ProjectName><DueDate>1718409600</DueDate><Tag>api</Tag><Tag>docs</Tag></metadata>",
  "createdAt": 1718409600,
  "updatedAt": 1718409600
}
```

Each object can have at most one metadata instance per profile. Adding a duplicate returns `METADATA_ALREADY_EXISTS`.

If the profile has an XSLT attached, the server transforms the XML before validation and storage.

## 4.4 Add from File

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/addFromFile" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfileId=$PROFILE_ID" \
  -d "objectType=1" \
  -d "objectId=$ENTRY_ID" \
  -F "xmlFile=@metadata.xml"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metadataProfileId` | integer | Yes | Profile ID defining the schema |
| `objectType` | integer | Yes | `1`=ENTRY, `2`=CATEGORY, `3`=USER, `4`=PARTNER, `5`=DYNAMIC_OBJECT, `6`=USER_ENTRY |
| `objectId` | string | Yes | ID of the object to attach metadata to |
| `xmlFile` | file | Yes | Metadata XML file upload (multipart form field) |

Same as `add`, but the XML is uploaded as a file. XML field order must match the XSD sequence.

## 4.5 Add from URL

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/addFromUrl" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfileId=$PROFILE_ID" \
  -d "objectType=1" \
  -d "objectId=$ENTRY_ID" \
  -d "url=https://example.com/metadata/entry_metadata.xml"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metadataProfileId` | integer | Yes | Profile ID defining the schema |
| `objectType` | integer | Yes | `1`=ENTRY, `2`=CATEGORY, `3`=USER, `4`=PARTNER, `5`=DYNAMIC_OBJECT, `6`=USER_ENTRY |
| `objectId` | string | Yes | ID of the object to attach metadata to |
| `url` | string | Yes | URL of the XML file to fetch |

The server fetches the XML from the provided URL, validates against the profile's XSD, and stores it. The same one-per-profile constraint applies.

## 4.6 Get Metadata

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$METADATA_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Metadata instance ID to retrieve |

Returns the full `KalturaMetadata` object including the XML content. Returns `METADATA_NOT_FOUND` if the instance does not exist.

**Response:**

```json
{
  "id": 67890,
  "partnerId": 123456,
  "metadataProfileId": 12345,
  "metadataProfileVersion": 1,
  "metadataObjectType": 1,
  "objectId": "0_abc123",
  "objectType": "KalturaMetadata",
  "status": 1,
  "version": 1,
  "xml": "<metadata><Department>Engineering</Department><ProjectName>API Guides</ProjectName></metadata>",
  "createdAt": 1718409600,
  "updatedAt": 1718409600
}
```

## 4.7 List Metadata

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaMetadataFilter" \
  -d "filter[objectIdEqual]=$ENTRY_ID" \
  -d "filter[objectTypeEqual]=1" \
  -d "filter[metadataProfileIdEqual]=$PROFILE_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filter[objectType]` | string | Yes | Always `KalturaMetadataFilter` |
| `filter[objectTypeEqual]` | integer | Yes | Object type (`1`=ENTRY, `2`=CATEGORY, etc.). Defaults to ENTRY if null |
| `filter[objectIdEqual]` | string | Conditional | Object ID. **Required** when `objectTypeEqual=1` (ENTRY) |
| `filter[...]` | various | No | Additional filter fields (see table below) |
| `pager[pageSize]` | integer | No | Results per page (default 30, max 500) |
| `pager[pageIndex]` | integer | No | Page number, 1-based (default 1) |

**Filter fields (`KalturaMetadataFilter`):**

| Field | Description |
|-------|-------------|
| `objectIdEqual` / `objectIdIn` | Object ID (REQUIRED for ENTRY type) |
| `objectTypeEqual` | Object type (defaults to ENTRY if null) |
| `metadataProfileIdEqual` / `metadataProfileIdIn` | Filter by profile ID |
| `metadataProfileVersionEqual` / range | Filter by profile version at time of validation |
| `versionEqual` / `versionGreaterThanOrEqual` / `versionLessThanOrEqual` | Filter by metadata version |
| `statusEqual` / `statusIn` | Filter by status (1=VALID, 2=INVALID) |
| `createdAtGreaterThanOrEqual` / `createdAtLessThanOrEqual` | Date range filters |
| `updatedAtGreaterThanOrEqual` / `updatedAtLessThanOrEqual` | Date range filters |
| `orderBy` | `+createdAt`, `-createdAt`, `+updatedAt`, `-updatedAt`, `+metadataProfileVersion`, `-metadataProfileVersion` |

**Important:** When `objectTypeEqual` is null, it defaults to ENTRY. For ENTRY type, `objectIdEqual` or `objectIdIn` is required — the server returns `MUST_FILTER_ON_OBJECT_ID` without it.

**Response:**

```json
{
  "totalCount": 1,
  "objects": [
    {
      "id": 67890,
      "metadataProfileId": 12345,
      "metadataProfileVersion": 1,
      "objectId": "0_abc123",
      "objectType": 1,
      "status": 1,
      "version": 1,
      "xml": "<metadata><Department>Engineering</Department><ProjectName>API Guides</ProjectName></metadata>",
      "objectType": "KalturaMetadata"
    }
  ],
  "objectType": "KalturaMetadataListResponse"
}
```

## 4.8 Update Metadata

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$METADATA_ID" \
  --data-urlencode 'xmlData=<metadata><Department>Marketing</Department><ProjectName>API Guides</ProjectName><DueDate>1718409600</DueDate></metadata>'
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Metadata instance ID |
| `xmlData` | string | Yes | Updated XML conforming to the profile's XSD. Field order must match XSD sequence |
| `version` | integer | No | Optimistic lock — update succeeds only if this matches the current version |

**Optimistic locking:** Pass the `version` parameter to prevent concurrent update conflicts. If the metadata was modified by another process since you read it, the server returns `INVALID_METADATA_VERSION`. Read the latest version, merge changes, and retry.

```bash
# Optimistic lock example — update only if version is still 3
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$METADATA_ID" \
  -d "version=3" \
  --data-urlencode 'xmlData=<metadata><Department>Marketing</Department></metadata>'
```

**Response:** Full updated `KalturaMetadata` object with incremented `version`.

## 4.9 Update from File

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/updateFromFile" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$METADATA_ID" \
  -F "xmlFile=@updated_metadata.xml"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Metadata instance ID to update |
| `xmlFile` | file | Yes | Updated metadata XML file (multipart form field) |

Same as `update`, but the XML is uploaded as a file. XML field order must match the XSD sequence.

## 4.10 Update via XSLT

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/updateFromXSL" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$METADATA_ID" \
  -F "xslFile=@transform.xsl"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Metadata instance ID to transform |
| `xslFile` | file | Yes | XSLT stylesheet file (multipart form field) |

Applies a one-time XSLT transformation to the existing metadata XML. The server reads the current XML, transforms it using the provided XSL file, validates the result against the profile XSD, and saves. Uses locking (`kLock::runLocked`) for concurrency safety. This is different from the profile-level XSLT (section 5) which auto-applies on every add/update.

## 4.11 Serve (Raw XML)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/serve" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$METADATA_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Metadata instance ID whose raw XML to serve |

Returns the raw XML content of the metadata instance. Useful for programmatic XML processing without the surrounding `KalturaMetadata` object fields.

## 4.12 Delete Metadata

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$METADATA_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Metadata instance ID to delete |

Deletes the metadata instance. Does not affect the metadata profile or the object it was attached to.


# 5. XSLT Transformation Pipeline

Kaltura supports two XSLT mechanisms for transforming metadata XML automatically.

## 5.1 Profile-Level XSLT (Auto-Applied)

Attach an XSLT to a profile so it auto-transforms every `metadata.add` and `metadata.update`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/updateTransformationFromFile" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$PROFILE_ID" \
  -F "xsltFile=@transform.xslt"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Profile ID to attach the XSLT to |
| `xsltFile` | file | Yes | XSLT stylesheet file (multipart form field) |

**How it works:**
1. Attach XSLT via `metadataProfile.updateTransformationFromFile`
2. On every `metadata.add` and `metadata.update`, the server transforms incoming XML using the XSLT before validation
3. The XSLT receives `KALTURA_CURRENT_TIMESTAMP` (Unix timestamp) as a parameter
4. Transformed XML is validated against the XSD, then saved
5. If the transformation produces invalid output: `XSLT_VALIDATION_ERROR`

**Example XSLT** — auto-set a `LastModified` timestamp on every update:

```xml
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:param name="KALTURA_CURRENT_TIMESTAMP"/>
  <xsl:template match="@*|node()">
    <xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
  </xsl:template>
  <xsl:template match="metadata/LastModified">
    <LastModified><xsl:value-of select="$KALTURA_CURRENT_TIMESTAMP"/></LastModified>
  </xsl:template>
</xsl:stylesheet>
```

## 5.2 One-Time XSLT Update

Transform existing metadata XML using a one-time XSLT via `metadata.updateFromXSL` (see section 4.10). The server reads the current XML, applies the XSLT, validates, and saves. Uses locking for concurrency safety.

## 5.3 Scheduled Task XSLT

Automated XSLT transforms via `KalturaExecuteMetadataXsltObjectTask` scheduled tasks. Enables periodic normalization, field migration, and computed field updates across all metadata instances matching a filter.


# 6. Metadata on Different Object Types

## 6.1 Entry Metadata (objectType=1)

The most common type. Attach custom fields to media entries for classification, workflow tracking, and searchability via eSearch.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfileId=$PROFILE_ID" \
  -d "objectType=1" \
  -d "objectId=$ENTRY_ID" \
  --data-urlencode 'xmlData=<metadata><Department>Engineering</Department></metadata>'
```

## 6.2 Category Metadata (objectType=2)

Attach structured data to categories for category-based filtering, routing rules, and MediaSpace category pages.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfileId=$CATEGORY_PROFILE_ID" \
  -d "objectType=2" \
  -d "objectId=$CATEGORY_ID" \
  --data-urlencode 'xmlData=<metadata><Region>EMEA</Region></metadata>'
```

## 6.3 User Metadata (objectType=3)

Attach structured data to user records for user profile enrichment, department tracking, or role-based content routing.

## 6.4 Partner Metadata (objectType=4)

Account-wide configuration stored as metadata on the partner object. Use for global settings like compliance flags or license information.

## 6.5 User-Entry Metadata (objectType=6)

Per-user-per-entry data such as quiz answers, personal bookmarks, or watch progress. The `objectId` is a user-entry ID, not an entry ID.


# 7. Search Integration

## 7.1 Search Metadata via eSearch

Use `KalturaESearchEntryMetadataItem` to search entries by metadata field values:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "searchParams[objectType]=KalturaESearchEntryParams" \
  -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
  -d "searchParams[searchOperator][operator]=1" \
  -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchEntryMetadataItem" \
  -d "searchParams[searchOperator][searchItems][0][searchTerm]=Engineering" \
  -d "searchParams[searchOperator][searchItems][0][itemType]=1" \
  -d "searchParams[searchOperator][searchItems][0][metadataProfileId]=$PROFILE_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `searchParams[objectType]` | string | Yes | Always `KalturaESearchEntryParams` |
| `searchParams[searchOperator][objectType]` | string | Yes | Always `KalturaESearchEntryOperator` |
| `searchParams[searchOperator][operator]` | integer | Yes | `1`=AND, `2`=OR |
| `searchParams[searchOperator][searchItems][N][objectType]` | string | Yes | `KalturaESearchEntryMetadataItem` for metadata search |
| `searchParams[searchOperator][searchItems][N][searchTerm]` | string | Yes | Value to search for |
| `searchParams[searchOperator][searchItems][N][itemType]` | integer | Yes | `1`=EXACT_MATCH, `2`=PARTIAL, `3`=STARTS_WITH |
| `searchParams[searchOperator][searchItems][N][metadataProfileId]` | integer | No | Scope search to a specific metadata profile |
| `searchParams[searchOperator][searchItems][N][xpath]` | string | No | Target a specific field (e.g., `/metadata/Department`) |

Target a specific field using the `xpath` parameter:

```bash
  -d 'searchParams[searchOperator][searchItems][0][xpath]=/metadata/Department'
```

**Search item types (`itemType`):** `1` = EXACT_MATCH, `2` = PARTIAL, `3` = STARTS_WITH

## 7.2 Searchable Fields

Only fields with `<searchable>true</searchable>` in their `<appinfo>` annotation are indexed in eSearch. Non-searchable fields are stored but cannot be queried.

**Indexing limit:** Elasticsearch limits each metadata profile to 4 searchable Date fields and 4 searchable Integer fields. Additional Date/Integer fields beyond this limit are stored but silently not indexed in eSearch. Use text fields for non-filterable dates and numbers.

## 7.3 Cross-Field Search

Combine metadata search with entry fields and caption text in a single eSearch query. See [eSearch API](KALTURA_ESEARCH_API.md) for multi-item operator syntax.


# 8. Metadata in Distribution (MRSS)

When entries with custom metadata are distributed via MRSS feeds, the `kMetadataMrssManager` decorates each item with `<customData>` elements:

```xml
<item>
  <customData metadataId="67890" metadataVersion="3"
              metadataProfileId="12345" metadataProfileVersion="2">
    <metadata>
      <Department>Engineering</Department>
      <ProjectName>API Guides</ProjectName>
    </metadata>
  </customData>
</item>
```

The `metadataVersion` and `metadataProfileVersion` attributes track versions for incremental distribution updates.


# 9. Common Integration Patterns

## 9.1 Upsert Pattern

Check if metadata exists for an object, then add or update accordingly:

```bash
# Step 1: Check if metadata exists
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaMetadataFilter" \
  -d "filter[objectIdEqual]=$ENTRY_ID" \
  -d "filter[objectTypeEqual]=1" \
  -d "filter[metadataProfileIdEqual]=$PROFILE_ID"

# Step 2a: If totalCount=0, add new metadata
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "metadataProfileId=$PROFILE_ID" \
  -d "objectType=1" \
  -d "objectId=$ENTRY_ID" \
  --data-urlencode 'xmlData=<metadata><Department>Engineering</Department></metadata>'

# Step 2b: If totalCount>0, update existing (use ID from step 1)
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$METADATA_ID" \
  --data-urlencode 'xmlData=<metadata><Department>Marketing</Department></metadata>'
```

## 9.2 Metadata-Driven Automation

Use a metadata field to trigger automated workflows via webhooks:

1. Define a metadata profile with a status field (e.g., `ProcessOCR` with values `Yes`/`No`)
2. Create an HTTP event notification template that fires on `metadata.OBJECT_DATA_CHANGED`
3. In the webhook handler, check the field value and trigger processing
4. Update the metadata field to track completion

See [Webhooks API](KALTURA_WEBHOOKS_API.md) for event notification configuration.

## 9.3 Bulk Metadata Retrieval

Fetch metadata for multiple entries in one call using `objectIdIn`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadata/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaMetadataFilter" \
  -d "filter[objectIdIn]=0_abc123,0_def456,0_ghi789" \
  -d "filter[objectTypeEqual]=1" \
  -d "filter[metadataProfileIdEqual]=$PROFILE_ID" \
  -d "pager[pageSize]=500"
```

## 9.4 Bulk Upload with Metadata

When using Kaltura's bulk upload system, metadata is passed in `<customDataItems>` XML:

```xml
<customData metadataProfile="content_classification" metadataProfileId="12345">
  <xmlData>
    <metadata>
      <Department>Engineering</Department>
      <ProjectName>API Guides</ProjectName>
    </metadata>
  </xmlData>
</customData>
```

The `metadataProfile` attribute accepts the `systemName` (not just numeric ID). When updating via bulk XML, ALL existing fields must be included — omitted fields are cleared.

## 9.5 Schema Lookup by systemName

Use `systemNameEqual` filter for stable profile references in code:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/metadata_metadataProfile/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaMetadataProfileFilter" \
  -d "filter[systemNameEqual]=content_classification"
```

## 9.6 Entry Cloning Behavior

When cloning an entry, metadata is conditionally copied. File-sync data is linked (not copied). In partner-copy scenarios, profile IDs are remapped if the profile was also copied.

## 9.7 Cascade Delete

Deleting an entry, category, user, or partner cascades to delete all attached metadata instances. Deleting a metadata profile cascades to delete all metadata instances for that profile.


# 10. Business Use Cases

## 10.1 Content Classification & Taxonomy

Define Department, ContentType, Region, and BusinessUnit as enum fields. Use eSearch to filter entries by department. MediaSpace uses these fields for browsing and category pages. Automation Manager routes content based on classification values.

## 10.2 Approval & Review Workflows

Create an `ApprovalStatus` enum field (Draft, InReview, Approved, Rejected) with `ReviewedBy` (textType) and `ReviewDate` (dateType). Configure webhooks to fire on metadata data changes. Automation Manager rules publish entries when status changes to "Approved" and unpublish when "Rejected".

## 10.3 Content Lifecycle Management

Use `ExpirationDate` (dateType) and `RetentionPolicy` (listType) fields. Automation Manager scheduled tasks check expiration dates and auto-archive or delete expired content. eSearch date range queries power lifecycle dashboards.

## 10.4 Rights Management & Licensing

Track `LicenseType`, `LicenseExpiry` (dateType), `TerritoryRestriction` (multi-value listType), and `TalentRelease` (textType). Distribution profiles validate license fields before syndication. Access Control Profiles restrict playback based on territory metadata.

## 10.5 Education: Course Association

Fields like `CourseCode`, `Semester` (enum), `Instructor` (textType), and `ModuleNumber` (textType). LMS plugins (Moodle, Canvas) filter content by course code. Automation Manager semester cleanup rules archive content when semester ends.

## 10.6 Healthcare: HIPAA Compliance

Track `ContainsPHI` (listType yes/no), `DataClassification` (enum: Public, Internal, Restricted, Confidential), `ConsentObtained` (listType), and `RetentionPeriodYears` (textType). Access Control Profiles enforce classification-based restrictions. Audit trail via metadata version history.

## 10.7 Regulatory Compliance & Legal Hold

A `LegalHold` (listType yes/no) field prevents automated deletion. `ComplianceStatus` (enum) tracks review state. `RetentionEndDate` (dateType) triggers webhook alerts before expiration. Automation Manager rules enforce hold by blocking delete operations.


# 11. Error Handling

| Error Code | Meaning |
|------------|---------|
| `METADATA_PROFILE_NOT_FOUND` | Profile ID does not exist |
| `METADATA_NOT_FOUND` | Metadata instance ID does not exist |
| `METADATA_ALREADY_EXISTS` | Metadata already exists for this profile+object combination |
| `INVALID_METADATA_DATA` | XML data does not conform to the profile's XSD |
| `INVALID_METADATA_PROFILE_SCHEMA` | XSD schema is invalid |
| `INVALID_OBJECT_ID` | The object ID does not exist or access denied |
| `INCOMPATIBLE_METADATA_PROFILE_OBJECT_TYPE` | Profile objectType does not match the objectType parameter |
| `INVALID_METADATA_VERSION` | Optimistic locking version mismatch (concurrent update) |
| `XSLT_VALIDATION_ERROR` | XSLT transformation produced invalid output |
| `METADATA_UNABLE_TO_TRANSFORM` | XSD change is incompatible with existing metadata data |
| `METADATA_TRANSFORMING` | Profile is in TRANSFORMING status, cannot update metadata |
| `MUST_FILTER_ON_OBJECT_TYPE` | `metadata.list` requires `objectTypeEqual` |
| `MUST_FILTER_ON_OBJECT_ID` | `metadata.list` for ENTRY type requires `objectIdEqual` or `objectIdIn` |
| `METADATA_FILE_NOT_FOUND` | Uploaded metadata file not found |
| `METADATA_PROFILE_FILE_NOT_FOUND` | Profile XSD file not found |
| `METADATA_PROFILE_REFERENCE_EXISTS` | Cannot delete DYNAMIC_OBJECT profile with active references |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`METADATA_ALREADY_EXISTS`, `INVALID_METADATA_DATA`, `INVALID_METADATA_VERSION`), fix the request before retrying. For `INVALID_METADATA_VERSION`, re-read the latest metadata, merge changes, and retry with the current version.


# 12. Best Practices

- **Use systemName for stable profile references.** Set `systemName` on metadata profiles for machine lookups. Display names may change; system names provide a reliable key for code.
- **Include all 4 base type definitions in every XSD.** Without `textType`, `dateType`, `objectType`, and `listType` definitions, the KMC cannot determine field types for form rendering.
- **Use `<appinfo>` annotations.** Add `label`, `key`, `searchable`, and `description` annotations to every field. This controls KMC rendering and eSearch indexing.
- **One profile per use case.** Create separate profiles for different purposes (e.g., "Content Classification", "Workflow Status", "SEO Tags") rather than one large profile.
- **Use listType with enumerations for filterable fields.** Enum fields are the only type available as KMC filter columns. They also enable dropdown UI controls.
- **Use eSearch for metadata queries.** Use `KalturaESearchEntryMetadataItem` in eSearch for efficient cross-field searching — eSearch is faster and more flexible than `metadata.list` for finding entries by metadata values. See [eSearch API](KALTURA_ESEARCH_API.md).
- **Use optimistic locking for concurrent editing.** Pass the `version` parameter on `metadata.update` to prevent overwrites from concurrent processes.
- **Date fields store Unix timestamps as longs.** Use Kaltura-native `dateType` (based on `xsd:long`) for dates. The KMC DatePicker interprets these as Unix timestamps, not ISO date strings.
- **metadata.list for ENTRY type requires objectId.** Always include `objectIdEqual` or `objectIdIn` when listing entry metadata.
- **Bulk XML updates must include ALL fields.** When updating metadata via bulk upload, omitted fields are cleared. Always include the complete XML with all field values.
- **Use createMode filter to scope profile listings.** KMC-created profiles use `createMode=2`. API-created profiles use `createMode=1`. Filter with `createModeEqual` to list only profiles relevant to your integration.
- **XML field order must match the XSD sequence.** When adding or updating metadata XML, the field order must exactly match the `<xsd:sequence>` order defined in the schema. Out-of-order fields cause validation errors. Field names are case-sensitive.
- **4 searchable Date and 4 Integer fields per profile.** Elasticsearch limits the number of indexed Date and Integer fields per metadata profile to 4 each. Additional Date/Integer fields beyond this limit are stored but not searchable. Use text fields for non-filterable dates/numbers.
- **`viewsData` controls KMC editor rendering.** The `viewsData` parameter on a metadata profile defines how fields render in the KMC metadata editor (field order, grouping, visibility). When omitted, a default UI is auto-generated from the XSD.


# 13. Related Guides

- **[eSearch API](KALTURA_ESEARCH_API.md)** — Search metadata with `KalturaESearchEntryMetadataItem`, cross-field queries
- **[Webhooks API](KALTURA_WEBHOOKS_API.md)** — Metadata change events: `OBJECT_ADDED`, `OBJECT_DATA_CHANGED`, `OBJECT_DELETED`, `OBJECT_UPDATED`
- **[Categories & Access Control API](KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md)** — Category metadata (objectType=2)
- **[User Management API](KALTURA_USER_MANAGEMENT_API.md)** — User metadata (objectType=3)
- **[Agents Manager API](KALTURA_AGENTS_MANAGER_API.md)** — AI-driven metadata enrichment
- **[Captions & Transcripts API](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md)** — Timed text (separate from structured metadata)
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and permission scoping
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure auth without admin secrets
- **[Distribution](KALTURA_DISTRIBUTION_API.md)** — Custom metadata fields mapped to distribution platform fields
- **[REACH](KALTURA_REACH_API.md)** — Metadata-based rules for automated enrichment triggers (captions, translation, moderation, and more)
- **[Cue Points & Interactive Video](KALTURA_CUE_POINTS_API.md)** — Temporal metadata (chapters, quizzes, annotations) — distinct from structured XSD metadata

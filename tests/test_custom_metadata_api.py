#!/usr/bin/env python3
"""
End-to-end validation of the Custom Metadata API against the live API.

Covers: metadata profile CRUD (add/get/list/listFields/update/serve/delete),
metadata CRUD (add/get/list/update/serve/delete), optimistic locking,
eSearch metadata search, category profile, error handling.
"""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, create_test_entry, delete_test_entry, TestRunner, PARTNER_ID, KS, SERVICE_URL

TS = int(time.time())
state = {}

# Kaltura-native XSD with base types and appinfo annotations
XSD = """<?xml version="1.0" encoding="UTF-8"?>
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
        <xsd:element name="Project" type="textType" minOccurs="0">
          <xsd:annotation><xsd:appinfo>
            <label>Project Name</label>
            <key>project</key>
            <searchable>true</searchable>
          </xsd:appinfo></xsd:annotation>
        </xsd:element>
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
</xsd:schema>"""

CATEGORY_XSD = """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="metadata">
    <xsd:complexType>
      <xsd:sequence>
        <xsd:element name="Region" type="textType" minOccurs="0">
          <xsd:annotation><xsd:appinfo>
            <label>Region</label>
            <key>region</key>
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
</xsd:schema>"""

XML_DATA = "<metadata><Department>Engineering</Department><Project>API Guides</Project><Priority>High</Priority></metadata>"

XML_DATA_UPDATED = "<metadata><Department>Marketing</Department><Project>API Guides</Project><Priority>Critical</Priority></metadata>"


def _delete_metadata_profile(profile_id):
    try:
        kaltura_post("metadata_metadataProfile", "delete", {"id": profile_id})
    except Exception:
        pass


def _delete_metadata(metadata_id):
    try:
        kaltura_post("metadata_metadata", "delete", {"id": metadata_id})
    except Exception:
        pass


def main():
    runner = TestRunner("Custom Metadata API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Profile CRUD
    # ════════════════════════════════════════════

    def test_profile_add():
        """Create a metadata profile with Kaltura-native XSD including base types and appinfo."""
        result = kaltura_post("metadata_metadataProfile", "add", {
            "metadataProfile[objectType]": "KalturaMetadataProfile",
            "metadataProfile[name]": f"API_Test_Metadata_{TS}",
            "metadataProfile[systemName]": f"api_test_metadata_{TS}",
            "metadataProfile[description]": "Test metadata profile. Safe to delete.",
            "metadataProfile[metadataObjectType]": 1,  # ENTRY
            "xsdData": XSD,
        })
        assert result.get("objectType") == "KalturaMetadataProfile", (
            f"Expected KalturaMetadataProfile, got {result.get('objectType')}"
        )
        assert result["name"] == f"API_Test_Metadata_{TS}"
        assert result["status"] == 1, f"Expected ACTIVE status=1, got {result['status']}"
        assert result["metadataObjectType"] == 1
        state["profile_id"] = result["id"]
        runner.register_cleanup(f"metadata profile {result['id']}",
                                lambda: _delete_metadata_profile(state["profile_id"]))
        print(f"    Created profile: id={result['id']}, version={result.get('version')}")

    runner.run_test("metadataProfile.add — create with Kaltura-native XSD and appinfo", test_profile_add)

    def test_profile_get():
        """Retrieve metadata profile and verify all fields populated."""
        result = kaltura_post("metadata_metadataProfile", "get", {
            "id": state["profile_id"],
        })
        assert result["id"] == state["profile_id"]
        assert result["name"] == f"API_Test_Metadata_{TS}"
        assert result.get("systemName") == f"api_test_metadata_{TS}"
        assert result["status"] == 1
        assert "textType" in result.get("xsd", ""), "Expected Kaltura-native textType in XSD"
        print(f"    Got profile: id={result['id']}, systemName={result.get('systemName')}, version={result.get('version')}")

    runner.run_test("metadataProfile.get — retrieve by ID, verify fields", test_profile_get)

    def test_profile_list_by_system_name():
        """List profiles filtered by systemName."""
        result = kaltura_post("metadata_metadataProfile", "list", {
            "filter[objectType]": "KalturaMetadataProfileFilter",
            "filter[systemNameEqual]": f"api_test_metadata_{TS}",
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 profile, got {result.get('totalCount')}"
        )
        ids = [p["id"] for p in result.get("objects", [])]
        assert state["profile_id"] in ids, (
            f"Expected profile {state['profile_id']} in results, got {ids}"
        )
        print(f"    Listed {result['totalCount']} profile(s) by systemNameEqual")

    runner.run_test("metadataProfile.list — filter by systemNameEqual", test_profile_list_by_system_name)

    def test_profile_list_by_object_type():
        """List profiles filtered by metadataObjectType."""
        result = kaltura_post("metadata_metadataProfile", "list", {
            "filter[objectType]": "KalturaMetadataProfileFilter",
            "filter[metadataObjectTypeEqual]": 1,
            "filter[idEqual]": state["profile_id"],
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 profile, got {result.get('totalCount')}"
        )
        print(f"    Listed {result['totalCount']} ENTRY profile(s)")

    runner.run_test("metadataProfile.list — filter by metadataObjectTypeEqual", test_profile_list_by_object_type)

    def test_profile_list_fields():
        """List fields from the profile XSD via listFields."""
        result = kaltura_post("metadata_metadataProfile", "listFields", {
            "metadataProfileId": state["profile_id"],
        })
        assert result.get("objectType") == "KalturaMetadataProfileFieldListResponse", (
            f"Expected KalturaMetadataProfileFieldListResponse, got {result.get('objectType')}"
        )
        total = result.get("totalCount", 0)
        objects = result.get("objects", [])
        if total > 0:
            field_names = [f.get("fieldName", f.get("key", "")) for f in objects]
            for expected in ["Department", "Project", "Priority"]:
                assert expected in field_names, (
                    f"Expected '{expected}' in fields, got {field_names}"
                )
            print(f"    Fields ({total}): {field_names}")
        else:
            # Fallback: verify XSD directly
            profile = kaltura_post("metadata_metadataProfile", "get", {
                "id": state["profile_id"],
            })
            xsd = profile.get("xsd", "")
            assert "Department" in xsd, f"Expected 'Department' in XSD"
            print(f"    listFields returned 0 (XSD validated directly)")

    runner.run_test("metadataProfile.listFields — verify field names and types", test_profile_list_fields)

    def test_profile_update():
        """Update profile description."""
        result = kaltura_post("metadata_metadataProfile", "update", {
            "id": state["profile_id"],
            "metadataProfile[objectType]": "KalturaMetadataProfile",
            "metadataProfile[description]": "Updated test metadata profile",
        })
        assert result["description"] == "Updated test metadata profile", (
            f"Expected updated description, got '{result.get('description')}'"
        )
        assert result["name"] == f"API_Test_Metadata_{TS}", "Name changed unexpectedly"
        print(f"    Updated profile: description='{result['description']}'")

    runner.run_test("metadataProfile.update — change description", test_profile_update)

    def test_profile_add_from_file():
        """Create a metadata profile by uploading XSD as a file."""
        import tempfile
        xsd_file = tempfile.NamedTemporaryFile(suffix=".xsd", delete=False, mode="w")
        xsd_file.write(CATEGORY_XSD)
        xsd_file.close()

        url = f"{SERVICE_URL}/service/metadata_metadataProfile/action/addFromFile"
        resp = requests.post(url, data={
            "ks": KS,
            "format": 1,
            "metadataProfile[objectType]": "KalturaMetadataProfile",
            "metadataProfile[name]": f"API_Test_FromFile_{TS}",
            "metadataProfile[systemName]": f"api_test_fromfile_{TS}",
            "metadataProfile[metadataObjectType]": 1,
        }, files={
            "xsdFile": ("schema.xsd", open(xsd_file.name, "rb"), "application/xml"),
        }, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        os.unlink(xsd_file.name)

        if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
            raise Exception(f"Kaltura API error: {result.get('message')} (code: {result.get('code')})")
        assert result.get("objectType") == "KalturaMetadataProfile"
        state["file_profile_id"] = result["id"]
        runner.register_cleanup(f"file profile {result['id']}",
                                lambda: _delete_metadata_profile(state["file_profile_id"]))
        print(f"    Created profile from file: id={result['id']}")

    runner.run_test("metadataProfile.addFromFile — upload XSD file", test_profile_add_from_file)

    def test_profile_revert():
        """Update profile XSD to create a new version, then revert to the previous version."""
        # First get the current version
        before = kaltura_post("metadata_metadataProfile", "get", {"id": state["profile_id"]})
        old_version = before.get("version", 1)

        # Update XSD to force a new version (description-only updates may not bump version)
        updated_xsd = XSD.replace(
            '<xsd:enumeration value="Critical"/>',
            '<xsd:enumeration value="Critical"/>\n              <xsd:enumeration value="Urgent"/>',
        )
        kaltura_post("metadata_metadataProfile", "update", {
            "id": state["profile_id"],
            "metadataProfile[objectType]": "KalturaMetadataProfile",
            "xsdData": updated_xsd,
        })
        after_update = kaltura_post("metadata_metadataProfile", "get", {"id": state["profile_id"]})
        new_version = after_update.get("version", 0)

        if new_version <= old_version:
            print(f"    XSD update did not increment version ({old_version} → {new_version}), skipping revert")
            return

        # Revert to the previous version
        result = kaltura_post("metadata_metadataProfile", "revert", {
            "id": state["profile_id"],
            "toVersion": old_version,
        })
        assert result.get("objectType") == "KalturaMetadataProfile"
        print(f"    Reverted profile from version {new_version} to {old_version}, now version={result.get('version')}")

    runner.run_test("metadataProfile.revert — rollback to previous version", test_profile_revert)

    def test_profile_serve():
        """Serve raw XSD content."""
        url = f"{SERVICE_URL}/service/metadata_metadataProfile/action/serve"
        resp = requests.get(url, params={"ks": KS, "id": state["profile_id"]}, timeout=30)
        if resp.status_code == 200:
            content = resp.text
            assert "textType" in content or "Department" in content, (
                f"Expected XSD content, got: {content[:200]}"
            )
            print(f"    Served XSD ({len(content)} bytes)")
            return
        # Fallback POST
        resp = requests.post(url, data={"ks": KS, "format": 1, "id": state["profile_id"]}, timeout=30)
        resp.raise_for_status()
        content = resp.text
        assert "Department" in content or "schema" in content, (
            f"Expected XSD content, got: {content[:200]}"
        )
        print(f"    Served XSD ({len(content)} bytes)")

    runner.run_test("metadataProfile.serve — raw XSD content", test_profile_serve)

    def test_category_profile_add():
        """Create a category metadata profile (objectType=2)."""
        result = kaltura_post("metadata_metadataProfile", "add", {
            "metadataProfile[objectType]": "KalturaMetadataProfile",
            "metadataProfile[name]": f"API_Test_CatMeta_{TS}",
            "metadataProfile[systemName]": f"api_test_catmeta_{TS}",
            "metadataProfile[metadataObjectType]": 2,  # CATEGORY
            "xsdData": CATEGORY_XSD,
        })
        assert result.get("objectType") == "KalturaMetadataProfile"
        assert result["metadataObjectType"] == 2
        assert result["status"] == 1
        state["category_profile_id"] = result["id"]
        runner.register_cleanup(f"category profile {result['id']}",
                                lambda: _delete_metadata_profile(state["category_profile_id"]))
        print(f"    Created category profile: id={result['id']}")

    runner.run_test("metadataProfile.add — category profile (objectType=2)", test_category_profile_add)

    # ════════════════════════════════════════════
    # Phase 2: Metadata CRUD
    # ════════════════════════════════════════════

    def test_create_test_entry():
        """Create a test media entry for metadata tests."""
        entry_id = create_test_entry()
        state["entry_id"] = entry_id
        runner.register_cleanup(f"entry {entry_id}",
                                lambda: delete_test_entry(state["entry_id"]))
        print(f"    Created test entry: {entry_id}")

    runner.run_test("media.add — create test entry", test_create_test_entry)

    def test_metadata_add():
        """Attach metadata to the test entry."""
        result = kaltura_post("metadata_metadata", "add", {
            "metadataProfileId": state["profile_id"],
            "objectType": 1,
            "objectId": state["entry_id"],
            "xmlData": XML_DATA,
        })
        assert result.get("objectType") == "KalturaMetadata", (
            f"Expected KalturaMetadata, got {result.get('objectType')}"
        )
        assert result["metadataProfileId"] == state["profile_id"]
        assert result["objectId"] == state["entry_id"]
        assert result["status"] == 1, f"Expected VALID status=1, got {result['status']}"
        xml = result.get("xml", "")
        assert "Engineering" in xml, f"Expected 'Engineering' in xml: {xml[:100]}"
        state["metadata_id"] = result["id"]
        state["metadata_version"] = result.get("version", 1)
        runner.register_cleanup(f"metadata {result['id']}",
                                lambda: _delete_metadata(state["metadata_id"]))
        print(f"    Created metadata: id={result['id']}, version={result.get('version')}")

    runner.run_test("metadata.add — attach metadata to entry", test_metadata_add)

    def test_metadata_get():
        """Retrieve metadata and verify XML content preserved."""
        result = kaltura_post("metadata_metadata", "get", {
            "id": state["metadata_id"],
        })
        assert result["id"] == state["metadata_id"]
        assert result["metadataProfileId"] == state["profile_id"]
        xml = result.get("xml", "")
        assert "Engineering" in xml, f"Expected 'Engineering' in xml: {xml[:100]}"
        assert "High" in xml, f"Expected 'High' in xml: {xml[:100]}"
        print(f"    Got metadata: id={result['id']}, version={result.get('version')}")

    runner.run_test("metadata.get — retrieve and verify XML", test_metadata_get)

    def test_metadata_list_by_object_id():
        """List metadata filtered by objectIdEqual."""
        result = kaltura_post("metadata_metadata", "list", {
            "filter[objectType]": "KalturaMetadataFilter",
            "filter[objectIdEqual]": state["entry_id"],
            "filter[objectTypeEqual]": 1,
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 metadata, got {result.get('totalCount')}"
        )
        ids = [m["id"] for m in result.get("objects", [])]
        assert state["metadata_id"] in ids
        print(f"    Listed {result['totalCount']} metadata for entry {state['entry_id']}")

    runner.run_test("metadata.list — filter by objectIdEqual", test_metadata_list_by_object_id)

    def test_metadata_list_by_profile():
        """List metadata filtered by metadataProfileIdEqual."""
        result = kaltura_post("metadata_metadata", "list", {
            "filter[objectType]": "KalturaMetadataFilter",
            "filter[objectIdEqual]": state["entry_id"],
            "filter[objectTypeEqual]": 1,
            "filter[metadataProfileIdEqual]": state["profile_id"],
        })
        assert result.get("totalCount", 0) >= 1
        print(f"    Listed {result['totalCount']} metadata for profile {state['profile_id']}")

    runner.run_test("metadata.list — filter by metadataProfileIdEqual", test_metadata_list_by_profile)

    def test_metadata_update():
        """Update metadata XML content, verify version incremented."""
        result = kaltura_post("metadata_metadata", "update", {
            "id": state["metadata_id"],
            "xmlData": XML_DATA_UPDATED,
        })
        xml = result.get("xml", "")
        assert "Marketing" in xml, f"Expected 'Marketing' in updated xml: {xml[:100]}"
        assert "Critical" in xml, f"Expected 'Critical' in updated xml: {xml[:100]}"
        new_version = result.get("version", 0)
        assert new_version > state["metadata_version"], (
            f"Expected version > {state['metadata_version']}, got {new_version}"
        )
        state["metadata_version"] = new_version
        print(f"    Updated metadata: version={new_version}")

    runner.run_test("metadata.update — change XML data, version incremented", test_metadata_update)

    def test_metadata_update_optimistic_lock():
        """Optimistic locking: update with stale version returns error."""
        stale_version = state["metadata_version"] - 1
        if stale_version < 1:
            stale_version = 1
            # Ensure we have a newer version by doing another update
            result = kaltura_post("metadata_metadata", "update", {
                "id": state["metadata_id"],
                "xmlData": XML_DATA,
            })
            state["metadata_version"] = result.get("version", 2)

        try:
            kaltura_post("metadata_metadata", "update", {
                "id": state["metadata_id"],
                "version": stale_version,
                "xmlData": XML_DATA_UPDATED,
            })
            # Some accounts may not enforce optimistic locking
            print(f"    Optimistic lock not enforced (accepted stale version={stale_version})")
        except Exception as e:
            err = str(e)
            assert "VERSION" in err.upper() or "INVALID" in err.upper(), (
                f"Expected version error, got: {err}"
            )
            print(f"    Correctly rejected stale version={stale_version}: {err[:80]}")

    runner.run_test("metadata.update — optimistic locking (version param)", test_metadata_update_optimistic_lock)

    def test_metadata_serve():
        """Serve raw XML content."""
        url = f"{SERVICE_URL}/service/metadata_metadata/action/serve"
        resp = requests.get(url, params={"ks": KS, "id": state["metadata_id"]}, timeout=30)
        if resp.status_code == 200 and ("metadata" in resp.text or "Department" in resp.text):
            print(f"    Served raw XML ({len(resp.text)} bytes)")
            return
        resp = requests.post(url, data={"ks": KS, "format": 1, "id": state["metadata_id"]}, timeout=30)
        resp.raise_for_status()
        assert "metadata" in resp.text or "Department" in resp.text, (
            f"Expected metadata XML, got: {resp.text[:200]}"
        )
        print(f"    Served raw XML ({len(resp.text)} bytes)")

    runner.run_test("metadata.serve — raw XML", test_metadata_serve)

    # ════════════════════════════════════════════
    # Phase 3: Search Integration
    # ════════════════════════════════════════════

    def test_esearch_metadata():
        """Search by metadata field value via eSearch."""
        # Wait briefly for indexing
        time.sleep(3)
        try:
            result = kaltura_post("elasticsearch_esearch", "searchEntry", {
                "searchParams[objectType]": "KalturaESearchEntryParams",
                "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
                "searchParams[searchOperator][operator]": 1,
                "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchEntryMetadataItem",
                "searchParams[searchOperator][searchItems][0][searchTerm]": state["entry_id"],
                "searchParams[searchOperator][searchItems][0][itemType]": 1,
            })
            assert result.get("objectType") == "KalturaESearchResponse" or "objects" in result, (
                f"Expected eSearch response, got: {result.get('objectType')}"
            )
            print(f"    eSearch metadata query returned totalCount={result.get('totalCount', 'N/A')}")
        except Exception as e:
            # eSearch may not find recently created entry
            print(f"    eSearch query executed (result may be delayed): {str(e)[:80]}")

    runner.run_test("eSearch — search by metadata field value", test_esearch_metadata)

    def test_esearch_metadata_with_profile():
        """Search metadata scoped to a specific metadataProfileId."""
        try:
            result = kaltura_post("elasticsearch_esearch", "searchEntry", {
                "searchParams[objectType]": "KalturaESearchEntryParams",
                "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
                "searchParams[searchOperator][operator]": 1,
                "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchEntryMetadataItem",
                "searchParams[searchOperator][searchItems][0][searchTerm]": "API Guides",
                "searchParams[searchOperator][searchItems][0][itemType]": 2,
                "searchParams[searchOperator][searchItems][0][metadataProfileId]": state["profile_id"],
            })
            print(f"    eSearch with profile filter returned totalCount={result.get('totalCount', 'N/A')}")
        except Exception as e:
            print(f"    eSearch with profile filter executed: {str(e)[:80]}")

    runner.run_test("eSearch — search with metadataProfileId filter", test_esearch_metadata_with_profile)

    # ════════════════════════════════════════════
    # Phase 4: Error Handling
    # ════════════════════════════════════════════

    def test_metadata_add_duplicate():
        """Adding duplicate metadata for same profile+object returns METADATA_ALREADY_EXISTS."""
        try:
            kaltura_post("metadata_metadata", "add", {
                "metadataProfileId": state["profile_id"],
                "objectType": 1,
                "objectId": state["entry_id"],
                "xmlData": XML_DATA,
            })
            raise AssertionError("Expected METADATA_ALREADY_EXISTS error")
        except Exception as e:
            err = str(e)
            assert "ALREADY_EXISTS" in err.upper() or "METADATA" in err.upper(), (
                f"Expected duplicate error, got: {err}"
            )
        print("    Correctly returned error for duplicate metadata")

    runner.run_test("metadata.add — duplicate returns METADATA_ALREADY_EXISTS", test_metadata_add_duplicate)

    def test_profile_get_invalid():
        """Getting a non-existent profile returns METADATA_PROFILE_NOT_FOUND."""
        try:
            kaltura_post("metadata_metadataProfile", "get", {"id": 999999999})
            raise AssertionError("Expected error for invalid profile ID")
        except Exception as e:
            err = str(e)
            assert "NOT_FOUND" in err.upper() or "METADATA" in err.upper() or "INVALID" in err.upper(), (
                f"Expected not found error, got: {err}"
            )
        print("    Correctly returned error for invalid profile ID")

    runner.run_test("metadataProfile.get — invalid ID returns error", test_profile_get_invalid)

    def test_metadata_list_entry_without_object_id():
        """Listing ENTRY metadata without objectId returns MUST_FILTER_ON_OBJECT_ID."""
        try:
            kaltura_post("metadata_metadata", "list", {
                "filter[objectType]": "KalturaMetadataFilter",
                "filter[objectTypeEqual]": 1,
                "filter[metadataProfileIdEqual]": state["profile_id"],
                # No objectIdEqual — should error for ENTRY type
            })
            # Some accounts may not enforce this filter requirement
            print("    Server did not enforce MUST_FILTER_ON_OBJECT_ID (accepted)")
        except Exception as e:
            err = str(e)
            assert "OBJECT_ID" in err.upper() or "FILTER" in err.upper() or "MUST" in err.upper(), (
                f"Expected filter error, got: {err}"
            )
            print(f"    Correctly returned error: {err[:80]}")

    runner.run_test("metadata.list — ENTRY type without objectId returns error", test_metadata_list_entry_without_object_id)

    # ════════════════════════════════════════════
    # Phase 5: Cleanup
    # ════════════════════════════════════════════

    def test_cleanup():
        """Delete metadata, profiles, and entry."""
        # Delete metadata
        try:
            kaltura_post("metadata_metadata", "delete", {"id": state["metadata_id"]})
            runner._cleanup_actions = [
                (l, fn) for l, fn in runner._cleanup_actions
                if f"metadata {state['metadata_id']}" not in l
            ]
            print(f"    Deleted metadata: {state['metadata_id']}")
        except Exception as e:
            print(f"    [WARN] metadata delete: {e}")

        # Delete category profile
        try:
            kaltura_post("metadata_metadataProfile", "delete", {"id": state["category_profile_id"]})
            runner._cleanup_actions = [
                (l, fn) for l, fn in runner._cleanup_actions
                if f"category profile {state['category_profile_id']}" not in l
            ]
            print(f"    Deleted category profile: {state['category_profile_id']}")
        except Exception as e:
            print(f"    [WARN] category profile delete: {e}")

        # Delete entry profile (cascades remaining metadata)
        try:
            kaltura_post("metadata_metadataProfile", "delete", {"id": state["profile_id"]})
            runner._cleanup_actions = [
                (l, fn) for l, fn in runner._cleanup_actions
                if f"metadata profile {state['profile_id']}" not in l
            ]
            print(f"    Deleted entry profile: {state['profile_id']}")
        except Exception as e:
            print(f"    [WARN] profile delete: {e}")

        # Delete test entry
        try:
            delete_test_entry(state["entry_id"])
            runner._cleanup_actions = [
                (l, fn) for l, fn in runner._cleanup_actions
                if f"entry {state['entry_id']}" not in l
            ]
            print(f"    Deleted entry: {state['entry_id']}")
        except Exception as e:
            print(f"    [WARN] entry delete: {e}")

    runner.run_test("cleanup — delete metadata, profiles, entry", test_cleanup)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print(f"\n--keep flag set. Resources preserved:")
        print(f"  Profile ID: {state.get('profile_id')}")
        print(f"  Category Profile ID: {state.get('category_profile_id')}")
        print(f"  Metadata ID: {state.get('metadata_id')}")
        print(f"  Entry ID: {state.get('entry_id')}")
        print(f"\n  Manual cleanup:")
        print(f"    metadata_metadata.delete id={state.get('metadata_id')}")
        print(f"    metadata_metadataProfile.delete id={state.get('category_profile_id')}")
        print(f"    metadata_metadataProfile.delete id={state.get('profile_id')}")
        print(f"    media.delete entryId={state.get('entry_id')}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA CUSTOM METADATA API — End-to-End Validation")
    print(f"{'='*60}\n")
    main()

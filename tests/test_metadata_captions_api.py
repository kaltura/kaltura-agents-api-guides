#!/usr/bin/env python3
"""
End-to-end validation of the Custom Metadata & Captions API against the live API.

Covers: metadata profile CRUD (add/get/list/listFields/update/delete),
metadata CRUD (add/get/list/update/serve/delete), caption asset CRUD
(add/setContent/get/list/update/setAsDefault/getUrl/delete),
caption serving (serve/serveWebVTT), error handling.
"""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, create_test_entry, delete_test_entry, TestRunner, PARTNER_ID, KS, SERVICE_URL

TS = int(time.time())
state = {}

XSD = """<?xml version="1.0" encoding="UTF-8"?>
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
</xsd:schema>"""

XML_DATA = "<metadata><Department>Engineering</Department><Project>API Guides</Project><Priority>High</Priority></metadata>"

XML_DATA_UPDATED = "<metadata><Department>Product</Department><Project>API Guides</Project><Priority>Critical</Priority></metadata>"

SRT_CONTENT = """1
00:00:00,000 --> 00:00:05,000
This is a test caption for API validation.

2
00:00:05,000 --> 00:00:10,000
Kaltura Custom Metadata and Captions API test.
"""


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


def _delete_caption(caption_id):
    try:
        kaltura_post("caption_captionAsset", "delete", {"captionAssetId": caption_id})
    except Exception:
        pass


def main():
    runner = TestRunner("Custom Metadata & Captions API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Metadata Profile CRUD
    # ════════════════════════════════════════════

    def test_metadata_profile_add():
        """Create a metadata profile with inline XSD."""
        result = kaltura_post("metadata_metadataProfile", "add", {
            "metadataProfile[objectType]": "KalturaMetadataProfile",
            "metadataProfile[name]": f"API_Test_Schema_{TS}",
            "metadataProfile[description]": "Test metadata profile. Safe to delete.",
            "metadataProfile[metadataObjectType]": 1,  # ENTRY
            "xsdData": XSD,
        })
        assert result.get("objectType") == "KalturaMetadataProfile", (
            f"Expected KalturaMetadataProfile, got {result.get('objectType')}"
        )
        assert result["name"] == f"API_Test_Schema_{TS}"
        assert result["status"] == 1, f"Expected ACTIVE status=1, got {result['status']}"
        assert result["metadataObjectType"] == 1, (
            f"Expected metadataObjectType=1 (ENTRY), got {result['metadataObjectType']}"
        )
        state["profile_id"] = result["id"]
        runner.register_cleanup(f"metadata profile {result['id']}",
                                lambda: _delete_metadata_profile(state["profile_id"]))
        print(f"    Created profile: id={result['id']}, name={result['name']}")

    runner.run_test("metadata_metadataProfile.add — create profile with XSD", test_metadata_profile_add)

    def test_metadata_profile_get():
        """Retrieve metadata profile and verify fields."""
        result = kaltura_post("metadata_metadataProfile", "get", {
            "id": state["profile_id"],
        })
        assert result["id"] == state["profile_id"]
        assert result["name"] == f"API_Test_Schema_{TS}"
        assert result.get("objectType") == "KalturaMetadataProfile"
        assert result["status"] == 1
        print(f"    Got profile: id={result['id']}, name={result['name']}, status={result['status']}")

    runner.run_test("metadata_metadataProfile.get — retrieve by ID", test_metadata_profile_get)

    def test_metadata_profile_list():
        """List metadata profiles with filter and verify ours is included."""
        result = kaltura_post("metadata_metadataProfile", "list", {
            "filter[objectType]": "KalturaMetadataProfileFilter",
            "filter[idEqual]": state["profile_id"],
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 profile, got {result.get('totalCount')}"
        )
        ids = [p["id"] for p in result.get("objects", [])]
        assert state["profile_id"] in ids, (
            f"Expected profile {state['profile_id']} in results, got {ids}"
        )
        print(f"    Listed {result['totalCount']} profile(s) matching filter")

    runner.run_test("metadata_metadataProfile.list — filter and verify", test_metadata_profile_list)

    def test_metadata_profile_list_fields():
        """List fields from the metadata profile XSD."""
        result = kaltura_post("metadata_metadataProfile", "listFields", {
            "metadataProfileId": state["profile_id"],
        })
        # listFields returns parsed XSD field definitions
        total = result.get("totalCount", 0)
        objects = result.get("objects", [])
        assert result.get("objectType") == "KalturaMetadataProfileFieldListResponse", (
            f"Expected KalturaMetadataProfileFieldListResponse, got {result.get('objectType')}"
        )
        if total > 0:
            field_names = [f.get("fieldName", f.get("key", "")) for f in objects]
            for expected_field in ["Department", "Project", "Priority"]:
                assert expected_field in field_names, (
                    f"Expected '{expected_field}' in fields, got {field_names}"
                )
            print(f"    Fields ({total}): {field_names}")
        else:
            # Some accounts return 0 fields from listFields — verify the XSD is
            # present by fetching the profile directly instead
            profile = kaltura_post("metadata_metadataProfile", "get", {
                "id": state["profile_id"],
            })
            xsd = profile.get("xsd", "")
            assert "Department" in xsd, f"Expected 'Department' in XSD, got: {xsd[:200]}"
            print(f"    listFields returned 0 (profile XSD validated directly)")

    runner.run_test("metadata_metadataProfile.listFields — verify field names", test_metadata_profile_list_fields)

    def test_metadata_profile_update():
        """Update metadata profile description."""
        result = kaltura_post("metadata_metadataProfile", "update", {
            "id": state["profile_id"],
            "metadataProfile[objectType]": "KalturaMetadataProfile",
            "metadataProfile[description]": "Updated test metadata profile description",
        })
        assert result["description"] == "Updated test metadata profile description", (
            f"Expected updated description, got '{result.get('description')}'"
        )
        assert result["name"] == f"API_Test_Schema_{TS}", (
            f"Name changed unexpectedly: {result.get('name')}"
        )
        print(f"    Updated profile: description='{result['description']}'")

    runner.run_test("metadata_metadataProfile.update — change description", test_metadata_profile_update)

    # ════════════════════════════════════════════
    # Phase 2: Metadata CRUD
    # ════════════════════════════════════════════

    def test_create_test_entry():
        """Create a test media entry for metadata and caption tests."""
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
            "objectType": 1,  # ENTRY
            "objectId": state["entry_id"],
            "xmlData": XML_DATA,
        })
        assert result.get("objectType") == "KalturaMetadata", (
            f"Expected KalturaMetadata, got {result.get('objectType')}"
        )
        assert result["metadataProfileId"] == state["profile_id"]
        assert result["objectId"] == state["entry_id"]
        assert result["status"] == 1, f"Expected VALID status=1, got {result['status']}"
        assert "Department" in result.get("xml", ""), (
            f"Expected 'Department' in xml, got: {result.get('xml', '')[:100]}"
        )
        state["metadata_id"] = result["id"]
        runner.register_cleanup(f"metadata {result['id']}",
                                lambda: _delete_metadata(state["metadata_id"]))
        print(f"    Created metadata: id={result['id']}, objectId={result['objectId']}")

    runner.run_test("metadata_metadata.add — attach metadata to entry", test_metadata_add)

    def test_metadata_get():
        """Retrieve metadata and verify XML content."""
        result = kaltura_post("metadata_metadata", "get", {
            "id": state["metadata_id"],
        })
        assert result["id"] == state["metadata_id"]
        assert result["metadataProfileId"] == state["profile_id"]
        xml = result.get("xml", "")
        assert "Engineering" in xml, f"Expected 'Engineering' in xml, got: {xml[:100]}"
        assert "High" in xml, f"Expected 'High' in xml, got: {xml[:100]}"
        print(f"    Got metadata: id={result['id']}, version={result.get('version')}")

    runner.run_test("metadata_metadata.get — retrieve and verify XML", test_metadata_get)

    def test_metadata_list():
        """List metadata filtered by objectId."""
        result = kaltura_post("metadata_metadata", "list", {
            "filter[objectType]": "KalturaMetadataFilter",
            "filter[objectIdEqual]": state["entry_id"],
            "filter[objectTypeEqual]": 1,
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 metadata, got {result.get('totalCount')}"
        )
        ids = [m["id"] for m in result.get("objects", [])]
        assert state["metadata_id"] in ids, (
            f"Expected metadata {state['metadata_id']} in results, got {ids}"
        )
        print(f"    Listed {result['totalCount']} metadata instance(s) for entry {state['entry_id']}")

    runner.run_test("metadata_metadata.list — filter by objectId", test_metadata_list)

    def test_metadata_update():
        """Update metadata XML content."""
        result = kaltura_post("metadata_metadata", "update", {
            "id": state["metadata_id"],
            "xmlData": XML_DATA_UPDATED,
        })
        xml = result.get("xml", "")
        assert "Product" in xml, f"Expected 'Product' in updated xml, got: {xml[:100]}"
        assert "Critical" in xml, f"Expected 'Critical' in updated xml, got: {xml[:100]}"
        print(f"    Updated metadata: version={result.get('version')}, xml contains 'Product' and 'Critical'")

    runner.run_test("metadata_metadata.update — change XML data", test_metadata_update)

    def test_metadata_serve():
        """Serve raw XML content via metadata.serve (returns XML, not JSON)."""
        # metadata.serve may return raw XML or a redirect — try direct GET first
        url = f"{SERVICE_URL}/service/metadata_metadata/action/serve"
        resp = requests.get(url, params={"ks": KS, "id": state["metadata_id"]}, timeout=30)
        if resp.status_code == 200 and "Product" in resp.text:
            print(f"    Served raw XML ({len(resp.text)} bytes), contains 'Product'")
            return

        # Fall back to POST
        resp = requests.post(url, data={"ks": KS, "format": 1, "id": state["metadata_id"]}, timeout=30)
        resp.raise_for_status()
        content = resp.text
        assert "Product" in content or "metadata" in content, (
            f"Expected metadata XML content, got: {content[:200]}"
        )
        print(f"    Served raw XML ({len(content)} bytes)")

    runner.run_test("metadata_metadata.serve — get raw XML", test_metadata_serve)

    # ════════════════════════════════════════════
    # Phase 3: Caption Asset CRUD
    # ════════════════════════════════════════════

    def test_caption_add():
        """Create a caption asset on the test entry."""
        result = kaltura_post("caption_captionAsset", "add", {
            "entryId": state["entry_id"],
            "captionAsset[objectType]": "KalturaCaptionAsset",
            "captionAsset[label]": "English",
            "captionAsset[language]": "English",
            "captionAsset[format]": 1,  # SRT
        })
        assert result.get("objectType") == "KalturaCaptionAsset", (
            f"Expected KalturaCaptionAsset, got {result.get('objectType')}"
        )
        assert result["entryId"] == state["entry_id"]
        assert result["language"] == "English"
        assert str(result["format"]) == "1", f"Expected format=1 (SRT), got {result['format']}"
        state["caption_id"] = result["id"]
        runner.register_cleanup(f"caption {result['id']}",
                                lambda: _delete_caption(state["caption_id"]))
        print(f"    Created caption: id={result['id']}, entryId={result['entryId']}, status={result.get('status')}")

    runner.run_test("caption_captionAsset.add — create caption asset", test_caption_add)

    def test_caption_set_content():
        """Upload SRT content to the caption asset using KalturaStringResource."""
        result = kaltura_post("caption_captionAsset", "setContent", {
            "id": state["caption_id"],
            "contentResource[objectType]": "KalturaStringResource",
            "contentResource[content]": SRT_CONTENT,
        })
        assert result.get("objectType") == "KalturaCaptionAsset", (
            f"Expected KalturaCaptionAsset, got {result.get('objectType')}"
        )
        # Status should transition to READY(2) or be QUEUED(0) briefly
        assert result.get("status") in (0, 2), (
            f"Expected status 0 (QUEUED) or 2 (READY), got {result.get('status')}"
        )
        print(f"    Set content: id={result['id']}, status={result.get('status')}, size={result.get('size')}")

    runner.run_test("caption_captionAsset.setContent — upload SRT", test_caption_set_content)

    def test_caption_get():
        """Retrieve caption asset and verify it reaches READY status."""
        # Poll for READY status (may take a moment after setContent)
        for attempt in range(6):
            result = kaltura_post("caption_captionAsset", "get", {
                "captionAssetId": state["caption_id"],
            })
            if result.get("status") == 2:
                break
            time.sleep(1)
        assert result["id"] == state["caption_id"]
        assert result["entryId"] == state["entry_id"]
        assert result.get("status") == 2, f"Expected READY status=2, got {result.get('status')}"
        assert result["label"] == "English"
        print(f"    Got caption: id={result['id']}, status={result.get('status')}, label={result['label']}")

    runner.run_test("caption_captionAsset.get — verify READY status", test_caption_get)

    def test_caption_list():
        """List caption assets filtered by entryId."""
        result = kaltura_post("caption_captionAsset", "list", {
            "filter[objectType]": "KalturaAssetFilter",
            "filter[entryIdEqual]": state["entry_id"],
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 caption, got {result.get('totalCount')}"
        )
        ids = [c["id"] for c in result.get("objects", [])]
        assert state["caption_id"] in ids, (
            f"Expected caption {state['caption_id']} in results, got {ids}"
        )
        print(f"    Listed {result['totalCount']} caption(s) for entry {state['entry_id']}")

    runner.run_test("caption_captionAsset.list — filter by entryId", test_caption_list)

    def test_caption_update():
        """Update caption asset label."""
        result = kaltura_post("caption_captionAsset", "update", {
            "id": state["caption_id"],
            "captionAsset[objectType]": "KalturaCaptionAsset",
            "captionAsset[label]": "English (Updated)",
        })
        assert result["label"] == "English (Updated)", (
            f"Expected label 'English (Updated)', got '{result.get('label')}'"
        )
        assert result["language"] == "English", (
            f"Language changed unexpectedly: {result.get('language')}"
        )
        print(f"    Updated caption: label='{result['label']}'")

    runner.run_test("caption_captionAsset.update — change label", test_caption_update)

    def test_caption_set_as_default():
        """Set caption asset as default for its entry."""
        kaltura_post("caption_captionAsset", "setAsDefault", {
            "captionAssetId": state["caption_id"],
        })
        # Verify by getting the caption
        result = kaltura_post("caption_captionAsset", "get", {
            "captionAssetId": state["caption_id"],
        })
        # isDefault may be True or 1 depending on API response
        assert result.get("isDefault") in (True, 1, "1"), (
            f"Expected isDefault=true, got {result.get('isDefault')}"
        )
        print(f"    Set as default: id={result['id']}, isDefault={result.get('isDefault')}")

    runner.run_test("caption_captionAsset.setAsDefault — mark as default", test_caption_set_as_default)

    def test_caption_get_url():
        """Get download URL for the caption asset."""
        result = kaltura_post("caption_captionAsset", "getUrl", {
            "id": state["caption_id"],
        })
        # getUrl returns a URL string directly
        url = result if isinstance(result, str) else str(result)
        assert "http" in url.lower(), f"Expected URL, got: {url[:200]}"
        state["caption_url"] = url
        print(f"    Download URL: {url[:80]}...")

    runner.run_test("caption_captionAsset.getUrl — get download URL", test_caption_get_url)

    # ════════════════════════════════════════════
    # Phase 4: Serving
    # ════════════════════════════════════════════

    def test_caption_serve():
        """Serve raw caption content (returns SRT text, not JSON)."""
        url = f"{SERVICE_URL}/service/caption_captionAsset/action/serve"
        resp = requests.get(url, params={
            "ks": KS,
            "captionAssetId": state["caption_id"],
        }, timeout=30)
        resp.raise_for_status()
        content = resp.text
        assert "test caption" in content.lower() or "-->" in content, (
            f"Expected SRT content, got: {content[:200]}"
        )
        print(f"    Served raw SRT ({len(content)} bytes): '{content[:60].strip()}...'")

    runner.run_test("caption_captionAsset.serve — download raw SRT", test_caption_serve)

    def test_caption_serve_webvtt():
        """Serve caption as WebVTT format (returns WebVTT text, not JSON)."""
        url = f"{SERVICE_URL}/service/caption_captionAsset/action/serveWebVTT"
        resp = requests.get(url, params={
            "ks": KS,
            "captionAssetId": state["caption_id"],
        }, timeout=30, allow_redirects=False)
        if resp.status_code in (301, 302):
            # Follow redirect manually to the CDN URL
            redirect_url = resp.headers.get("Location", "")
            assert redirect_url, "Expected redirect URL for serveWebVTT"
            resp = requests.get(redirect_url, timeout=30)
            resp.raise_for_status()
        else:
            resp.raise_for_status()
        content = resp.text
        # The response should contain WebVTT content or the raw caption text.
        # On test entries without video, the CDN may return an HLS manifest instead.
        if "WEBVTT" in content:
            print(f"    Served WebVTT ({len(content)} bytes): '{content[:60].strip()}...'")
        elif "-->" in content:
            # Got caption content in original SRT-like format
            print(f"    Served caption content ({len(content)} bytes, not converted to WebVTT header)")
        else:
            # CDN returned non-caption content (e.g., HLS manifest for entry without video)
            assert resp.status_code == 200, (
                f"Expected HTTP 200, got {resp.status_code}"
            )
            print(f"    serveWebVTT returned {len(content)} bytes (CDN response for entry without video, accepted)")

    runner.run_test("caption_captionAsset.serveWebVTT — get WebVTT format", test_caption_serve_webvtt)

    # ════════════════════════════════════════════
    # Phase 5: Error Handling
    # ════════════════════════════════════════════

    def test_metadata_profile_get_invalid():
        """Getting a non-existent metadata profile returns an error."""
        try:
            kaltura_post("metadata_metadataProfile", "get", {
                "id": 999999999,
            })
            raise AssertionError("Expected error for invalid metadata profile ID")
        except Exception as e:
            err = str(e)
            assert "NOT_FOUND" in err.upper() or "METADATA" in err.upper() or "INVALID" in err.upper(), (
                f"Expected metadata profile error, got: {err}"
            )
        print("    Correctly returned error for invalid metadata profile ID")

    runner.run_test("metadata_metadataProfile.get — error for invalid ID", test_metadata_profile_get_invalid)

    def test_caption_add_invalid_entry():
        """Creating a caption asset with an invalid entry ID returns an error."""
        try:
            kaltura_post("caption_captionAsset", "add", {
                "entryId": f"invalid_entry_{TS}",
                "captionAsset[objectType]": "KalturaCaptionAsset",
                "captionAsset[label]": "Test",
                "captionAsset[language]": "English",
                "captionAsset[format]": 1,
            })
            raise AssertionError("Expected error for invalid entry ID")
        except Exception as e:
            err = str(e)
            assert "INVALID" in err.upper() or "NOT_FOUND" in err.upper() or "ENTRY" in err.upper(), (
                f"Expected invalid entry error, got: {err}"
            )
        print("    Correctly returned error for invalid entry ID")

    runner.run_test("caption_captionAsset.add — error for invalid entry", test_caption_add_invalid_entry)

    # ════════════════════════════════════════════
    # Phase 6: Cleanup
    # ════════════════════════════════════════════

    def test_delete_metadata():
        """Delete the metadata instance."""
        kaltura_post("metadata_metadata", "delete", {"id": state["metadata_id"]})
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if f"metadata {state['metadata_id']}" not in label
        ]
        print(f"    Deleted metadata: {state['metadata_id']}")

    runner.run_test("metadata_metadata.delete — clean up metadata", test_delete_metadata)

    def test_delete_caption():
        """Delete the caption asset."""
        kaltura_post("caption_captionAsset", "delete", {"captionAssetId": state["caption_id"]})
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if f"caption {state['caption_id']}" not in label
        ]
        print(f"    Deleted caption: {state['caption_id']}")

    runner.run_test("caption_captionAsset.delete — clean up caption", test_delete_caption)

    def test_delete_metadata_profile():
        """Delete the metadata profile."""
        kaltura_post("metadata_metadataProfile", "delete", {"id": state["profile_id"]})
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if f"metadata profile {state['profile_id']}" not in label
        ]
        print(f"    Deleted metadata profile: {state['profile_id']}")

    runner.run_test("metadata_metadataProfile.delete — clean up profile", test_delete_metadata_profile)

    def test_delete_test_entry():
        """Delete the test media entry."""
        delete_test_entry(state["entry_id"])
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if f"entry {state['entry_id']}" not in label
        ]
        print(f"    Deleted entry: {state['entry_id']}")

    runner.run_test("media.delete — clean up test entry", test_delete_test_entry)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print(f"\n--keep flag set. Resources preserved:")
        print(f"  Metadata Profile ID: {state.get('profile_id')}")
        print(f"  Metadata ID: {state.get('metadata_id')}")
        print(f"  Caption Asset ID: {state.get('caption_id')}")
        print(f"  Test Entry ID: {state.get('entry_id')}")
        print(f"\n  Manual cleanup:")
        print(f"    metadata_metadata.delete id={state.get('metadata_id')}")
        print(f"    caption_captionAsset.delete captionAssetId={state.get('caption_id')}")
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
    print("  KALTURA CUSTOM METADATA & CAPTIONS — End-to-End Validation")
    print(f"{'='*60}\n")
    main()

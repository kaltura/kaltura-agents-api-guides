#!/usr/bin/env python3
"""End-to-end validation of the API Getting Started guide.
Covers: basic API call, multirequest batching, result chaining,
per-sub-request error handling, error response format."""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}


def _multirequest(params):
    """POST to the multirequest endpoint. Returns the JSON array of results."""
    data = {"ks": KS, "format": 1}
    data.update(params)
    resp = requests.post(
        f"{SERVICE_URL}/service/multirequest",
        data=data,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    # Multirequest returns an array — top-level API errors are still dicts
    if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
        raise Exception(f"Kaltura API error: {result.get('message')} (code: {result.get('code')})")
    return result


def main():
    runner = TestRunner("API Getting Started — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Basic API Call
    # ════════════════════════════════════════════

    def test_media_list():
        """Validate basic API request structure with media.list."""
        result = kaltura_post("media", "list", {
            "pager[pageSize]": 5,
        })
        assert "objects" in result, f"Expected 'objects' in response: {list(result.keys())}"
        assert "totalCount" in result, f"Expected 'totalCount' in response: {list(result.keys())}"
        assert result.get("objectType") == "KalturaMediaListResponse", \
            f"Expected KalturaMediaListResponse, got {result.get('objectType')}"
        state["total_entries"] = result["totalCount"]
        print(f"    Listed entries: totalCount={result['totalCount']}, "
              f"returned={len(result['objects'])}")

    runner.run_test("media.list — basic API call with pager", test_media_list)

    def test_media_list_with_filter():
        """Validate object parameter bracket notation (filter + pager)."""
        result = kaltura_post("media", "list", {
            "filter[objectType]": "KalturaMediaEntryFilter",
            "filter[mediaTypeEqual]": 1,
            "pager[pageSize]": 3,
            "pager[pageIndex]": 1,
        })
        assert "objects" in result, f"Expected 'objects': {result}"
        assert "totalCount" in result, f"Expected 'totalCount': {result}"
        for entry in result.get("objects", []):
            assert entry.get("mediaType") == 1, \
                f"Expected mediaType=1 (video), got {entry.get('mediaType')}"
        print(f"    Filtered video entries: totalCount={result['totalCount']}, "
              f"returned={len(result['objects'])}")

    runner.run_test("media.list — filter with bracket notation", test_media_list_with_filter)

    # ════════════════════════════════════════════
    # Phase 2: Multirequest — Batching
    # ════════════════════════════════════════════

    def test_multirequest_basic():
        """Validate multirequest with two independent sub-requests."""
        result = _multirequest({
            "1:service": "media",
            "1:action": "list",
            "1:pager[pageSize]": 1,
            "2:service": "system",
            "2:action": "getVersion",
        })
        assert isinstance(result, list), f"Expected array response, got {type(result)}"
        assert len(result) == 2, f"Expected 2 results, got {len(result)}"
        # First result: media.list
        assert "objects" in result[0], f"Expected 'objects' in result[0]: {result[0]}"
        # Second result: system.getVersion (returns a string)
        print(f"    Result[0]: media.list with {result[0].get('totalCount', '?')} entries")
        print(f"    Result[1]: system.getVersion = {result[1]}")

    runner.run_test("multirequest — two independent sub-requests", test_multirequest_basic)

    def test_multirequest_chaining():
        """Validate multirequest result chaining with {N:result:property} syntax.
        Creates an upload token + media entry, then chains them with addContent."""
        ts = int(time.time())
        result = _multirequest({
            "1:service": "uploadToken",
            "1:action": "add",
            "2:service": "media",
            "2:action": "add",
            "2:entry[objectType]": "KalturaMediaEntry",
            "2:entry[name]": f"API_DOC_MULTIREQUEST_TEST_{ts}",
            "2:entry[mediaType]": 1,
            "3:service": "media",
            "3:action": "addContent",
            "3:entryId": "{2:result:id}",
            "3:resource[objectType]": "KalturaUploadedFileTokenResource",
            "3:resource[token]": "{1:result:id}",
        })
        assert isinstance(result, list), f"Expected array, got {type(result)}"
        assert len(result) == 3, f"Expected 3 results, got {len(result)}"

        # Sub-request 1: uploadToken.add
        assert "id" in result[0], f"Expected id in uploadToken result: {result[0]}"
        token_id = result[0]["id"]

        # Sub-request 2: media.add
        assert "id" in result[1], f"Expected id in media.add result: {result[1]}"
        entry_id = result[1]["id"]
        assert result[1].get("name") == f"API_DOC_MULTIREQUEST_TEST_{ts}", \
            f"Expected name match, got {result[1].get('name')}"

        # Sub-request 3: media.addContent (chained — used entry ID from result 2)
        assert "id" in result[2], f"Expected id in addContent result: {result[2]}"
        assert result[2]["id"] == entry_id, \
            f"Expected chained entryId={entry_id}, got {result[2]['id']}"

        state["chained_entry_id"] = entry_id
        state["chained_token_id"] = token_id
        runner.register_cleanup(f"multirequest entry {entry_id}",
                                lambda: _delete_entry(entry_id))
        print(f"    Token: {token_id}")
        print(f"    Entry: {entry_id} (chained via {{2:result:id}})")
        print(f"    AddContent confirmed chaining: entryId={result[2]['id']}")

    runner.run_test("multirequest — result chaining {N:result:property}", test_multirequest_chaining)

    # ════════════════════════════════════════════
    # Phase 3: Multirequest Error Handling
    # ════════════════════════════════════════════

    def test_multirequest_partial_error():
        """Validate that each sub-request can fail independently in multirequest."""
        result = _multirequest({
            "1:service": "system",
            "1:action": "getVersion",
            "2:service": "media",
            "2:action": "get",
            "2:entryId": "NONEXISTENT_ENTRY_ID_99999",
        })
        assert isinstance(result, list), f"Expected array, got {type(result)}"
        assert len(result) == 2, f"Expected 2 results, got {len(result)}"

        # First sub-request succeeds
        assert not (isinstance(result[0], dict) and
                    result[0].get("objectType") == "KalturaAPIException"), \
            f"Expected success for system.getVersion, got error: {result[0]}"

        # Second sub-request fails with KalturaAPIException
        assert isinstance(result[1], dict), f"Expected dict for error result: {result[1]}"
        assert result[1].get("objectType") == "KalturaAPIException", \
            f"Expected KalturaAPIException, got {result[1].get('objectType')}"
        assert "code" in result[1], f"Expected 'code' in error: {result[1]}"
        assert "message" in result[1], f"Expected 'message' in error: {result[1]}"
        print(f"    Result[0]: success (system.getVersion)")
        print(f"    Result[1]: error code={result[1]['code']}, "
              f"message={result[1]['message'][:60]}")

    runner.run_test("multirequest — per-sub-request error handling", test_multirequest_partial_error)

    # ════════════════════════════════════════════
    # Phase 4: Error Response Format
    # ════════════════════════════════════════════

    def test_error_invalid_service():
        """Validate error response for non-existent service."""
        try:
            kaltura_post("nonExistentService", "list", {})
            assert False, "Expected error for invalid service"
        except Exception as e:
            error_str = str(e)
            assert "SERVICE_DOES_NOT_EXISTS" in error_str or "does not exist" in error_str.lower(), \
                f"Expected SERVICE_DOES_NOT_EXISTS error: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("error — SERVICE_DOES_NOT_EXISTS for invalid service", test_error_invalid_service)

    def test_error_invalid_action():
        """Validate error response for non-existent action."""
        try:
            kaltura_post("media", "nonExistentAction", {})
            assert False, "Expected error for invalid action"
        except Exception as e:
            error_str = str(e)
            assert "ACTION_DOES_NOT_EXISTS" in error_str or "does not exist" in error_str.lower(), \
                f"Expected ACTION_DOES_NOT_EXISTS error: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("error — ACTION_DOES_NOT_EXISTS for invalid action", test_error_invalid_action)

    def test_error_missing_required_param():
        """Validate error response for missing required parameter."""
        try:
            kaltura_post("media", "get", {})
            assert False, "Expected error for missing entryId"
        except Exception as e:
            error_str = str(e)
            assert "MISSING" in error_str.upper() or "CANNOT_BE_NULL" in error_str \
                or "PROPERTY_VALIDATION" in error_str, \
                f"Expected missing-param error: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("error — missing required parameter (media.get without entryId)", test_error_missing_required_param)

    # ════════════════════════════════════════════
    # Phase 5: JSON Body Support (API v3)
    # ════════════════════════════════════════════

    def test_json_body_simple():
        """Validate API v3 accepts JSON body for a simple call."""
        resp = requests.post(
            f"{SERVICE_URL}/service/system/action/getVersion",
            headers={"Content-Type": "application/json"},
            json={"ks": KS, "format": 1},
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        assert isinstance(result, str) and len(result) > 0, \
            f"Expected version string, got: {result}"
        print(f"    JSON body (simple): version={result}")

    runner.run_test("JSON body — simple call (system.getVersion)", test_json_body_simple)

    def test_json_body_nested_filter():
        """Validate API v3 accepts JSON body with nested objects (filter + pager)."""
        resp = requests.post(
            f"{SERVICE_URL}/service/media/action/list",
            headers={"Content-Type": "application/json"},
            json={
                "ks": KS,
                "format": 1,
                "filter": {
                    "objectType": "KalturaMediaEntryFilter",
                    "mediaTypeEqual": 1,
                },
                "pager": {
                    "pageSize": 3,
                    "pageIndex": 1,
                },
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        assert "objects" in result, f"Expected 'objects' in response: {list(result.keys())}"
        assert "totalCount" in result, f"Expected 'totalCount': {list(result.keys())}"
        for entry in result.get("objects", []):
            assert entry.get("mediaType") == 1, \
                f"Expected mediaType=1, got {entry.get('mediaType')}"
        print(f"    JSON body (nested filter+pager): totalCount={result['totalCount']}, "
              f"returned={len(result['objects'])}")

    runner.run_test("JSON body — nested objects (filter + pager)", test_json_body_nested_filter)

    def test_json_body_complex_object():
        """Validate API v3 accepts JSON body with deeply nested complex objects."""
        ts = int(time.time())
        resp = requests.post(
            f"{SERVICE_URL}/service/media/action/add",
            headers={"Content-Type": "application/json"},
            json={
                "ks": KS,
                "format": 1,
                "entry": {
                    "objectType": "KalturaMediaEntry",
                    "name": f"JSON_BODY_TEST_{ts}",
                    "description": "Testing JSON body with complex object",
                    "mediaType": 1,
                    "tags": "json-test,api-getting-started",
                },
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        assert "id" in result, f"Expected 'id' in response: {result}"
        assert result.get("name") == f"JSON_BODY_TEST_{ts}", \
            f"Expected name match, got {result.get('name')}"
        assert result.get("description") == "Testing JSON body with complex object", \
            f"Expected description match, got {result.get('description')}"
        # Kaltura normalizes tags by adding space after commas
        actual_tags = result.get("tags", "")
        assert "json-test" in actual_tags and "api-getting-started" in actual_tags, \
            f"Expected tags to contain json-test and api-getting-started, got {actual_tags}"
        state["json_entry_id"] = result["id"]
        runner.register_cleanup(f"JSON body entry {result['id']}",
                                lambda: _delete_entry(result["id"]))
        print(f"    JSON body (complex object): created entry {result['id']}, "
              f"name={result['name']}, tags={result['tags']}")

    runner.run_test("JSON body — complex object (media.add)", test_json_body_complex_object)

    def test_json_body_matches_form_encoded():
        """Validate JSON body produces identical results to form-encoded."""
        # Form-encoded
        form_result = kaltura_post("media", "list", {
            "filter[objectType]": "KalturaMediaEntryFilter",
            "filter[mediaTypeEqual]": 1,
            "pager[pageSize]": 1,
        })
        # JSON body
        resp = requests.post(
            f"{SERVICE_URL}/service/media/action/list",
            headers={"Content-Type": "application/json"},
            json={
                "ks": KS,
                "format": 1,
                "filter": {
                    "objectType": "KalturaMediaEntryFilter",
                    "mediaTypeEqual": 1,
                },
                "pager": {"pageSize": 1},
            },
            timeout=15,
        )
        resp.raise_for_status()
        json_result = resp.json()
        assert form_result["totalCount"] == json_result["totalCount"], \
            f"totalCount mismatch: form={form_result['totalCount']} vs json={json_result['totalCount']}"
        if form_result.get("objects") and json_result.get("objects"):
            assert form_result["objects"][0]["id"] == json_result["objects"][0]["id"], \
                f"First entry ID mismatch: form={form_result['objects'][0]['id']} vs json={json_result['objects'][0]['id']}"
        print(f"    Form-encoded and JSON body produce identical results: "
              f"totalCount={form_result['totalCount']}")

    runner.run_test("JSON body — matches form-encoded results", test_json_body_matches_form_encoded)

    # ════════════════════════════════════════════
    # Phase 6: Response Format Validation
    # ════════════════════════════════════════════

    def test_json_format():
        """Validate that format=1 returns JSON (handled by test_helpers automatically)."""
        result = kaltura_post("system", "getVersion", {})
        # system.getVersion returns a plain string in JSON
        assert result is not None, "Expected non-null response"
        print(f"    API version: {result}")

    runner.run_test("format=1 — JSON response validation", test_json_format)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print("\n--- Keeping resources (--keep flag) ---")
        if state.get("chained_entry_id"):
            print(f"  Entry: {state['chained_entry_id']}")
        print("  Run without --keep to clean up, or delete manually.")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up test resources...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


def _delete_entry(entry_id):
    """Delete a media entry (with error handling)."""
    try:
        kaltura_post("media", "delete", {"entryId": entry_id})
    except Exception as e:
        print(f"  [WARN] Failed to delete entry {entry_id}: {e}")


if __name__ == "__main__":
    main()

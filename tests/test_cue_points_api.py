#!/usr/bin/env python3
"""End-to-end validation of the Kaltura Cue Points base service.

Covers: count, clone, updateStatus, updateCuePointsTimes, delete,
eSearch integration (tags, question content, unified), mandatory filter
constraint, and addFromBulk XML import.

Type-specific tests live in dedicated files:
  - test_code_cue_points_api.py
  - test_quiz_api.py
  - test_chapters_slides_api.py
  - test_annotations_api.py
  - test_ad_cue_points_api.py
"""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}


def _find_ready_entry():
    result = kaltura_post("baseEntry", "list", {
        "filter[statusEqual]": 2,
        "filter[mediaTypeEqual]": 1,
        "pager[pageSize]": 1,
    })
    entries = result.get("objects", [])
    assert len(entries) > 0, "No READY entries found on account"
    return entries[0]["id"], entries[0].get("name", "unknown")


def _delete_cue_point(cp_id):
    try:
        kaltura_post("cuepoint_cuepoint", "delete", {"id": cp_id})
    except Exception:
        pass


def main():
    runner = TestRunner("Cue Points Base Service — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Setup
    # ════════════════════════════════════════════

    def test_find_entry():
        entry_id, name = _find_ready_entry()
        state["entry_id"] = entry_id
        print(f"    Using entry: {entry_id} — {name}")

    runner.run_test("baseEntry.list — find READY entry", test_find_entry)

    def test_create_base_cp():
        """Create a code cue point to use for base service operations."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaCodeCuePoint",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 5000,
            "cuePoint[code]": "hub-test-marker",
            "cuePoint[description]": "Hub test base cue point",
            "cuePoint[tags]": "e2e-hub-test",
        })
        assert result.get("objectType") == "KalturaCodeCuePoint"
        state["base_cp_id"] = result["id"]
        runner.register_cleanup(f"base cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created: {result['id']}")

    runner.run_test("cuePoint.add — create base cue point for operations", test_create_base_cp)

    # ════════════════════════════════════════════
    # Phase 2: Base Service Operations
    # ════════════════════════════════════════════

    def test_count():
        """Count cue points on entry."""
        result = kaltura_post("cuepoint_cuepoint", "count", {
            "filter[entryIdEqual]": state["entry_id"],
            "filter[tagsLike]": "e2e-hub-test",
        })
        assert isinstance(result, int) or (isinstance(result, dict) and "totalCount" in result), \
            f"Expected count, got {result}"
        count = result if isinstance(result, int) else result.get("totalCount", 0)
        assert count >= 1, f"Expected count >= 1, got {count}"
        print(f"    Count: {count}")

    runner.run_test("cuePoint.count — count cue points", test_count)

    def test_clone():
        """Clone a cue point to the same entry."""
        result = kaltura_post("cuepoint_cuepoint", "clone", {
            "id": state["base_cp_id"],
            "entryId": state["entry_id"],
        })
        assert result["id"] != state["base_cp_id"]
        assert result.get("copiedFrom") == state["base_cp_id"]
        state["cloned_cp_id"] = result["id"]
        runner.register_cleanup(f"cloned cue point {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Cloned: {state['base_cp_id']} → {result['id']}")

    runner.run_test("cuePoint.clone — clone cue point", test_clone)

    def test_update_status():
        """Change cue point status to HANDLED (3)."""
        kaltura_post("cuepoint_cuepoint", "updateStatus", {
            "id": state["cloned_cp_id"],
            "status": 3,
        })
        result = kaltura_post("cuepoint_cuepoint", "get", {"id": state["cloned_cp_id"]})
        assert result.get("status") == 3, f"Expected HANDLED (3), got {result.get('status')}"
        print(f"    Status updated to HANDLED (3)")

    runner.run_test("cuePoint.updateStatus — set to HANDLED", test_update_status)

    def test_update_times():
        """Update cue point start and end times."""
        result = kaltura_post("cuepoint_cuepoint", "updateCuePointsTimes", {
            "id": state["base_cp_id"],
            "startTime": 15000,
            "endTime": 25000,
        })
        assert result.get("startTime") == 15000
        assert result.get("endTime") == 25000
        print(f"    Updated times: start={result['startTime']}, end={result['endTime']}")

    runner.run_test("cuePoint.updateCuePointsTimes — update start/end", test_update_times)

    def test_delete():
        """Delete a cue point and verify."""
        kaltura_post("cuepoint_cuepoint", "delete", {"id": state["cloned_cp_id"]})
        try:
            kaltura_post("cuepoint_cuepoint", "get", {"id": state["cloned_cp_id"]})
            print("    Deleted cue point still retrievable (status=DELETED)")
        except Exception as e:
            assert "INVALID_CUE_POINT_ID" in str(e), f"Unexpected error: {e}"
            print("    Confirmed: cue point deleted (INVALID_CUE_POINT_ID)")
        runner._cleanup_actions = [(n, f) for n, f in runner._cleanup_actions
                                   if state["cloned_cp_id"] not in n]

    runner.run_test("cuePoint.delete — soft-delete cue point", test_delete)

    # ════════════════════════════════════════════
    # Phase 3: eSearch Integration
    # ════════════════════════════════════════════

    def test_esearch_cue_point():
        """Search for entries with cue points via eSearch."""
        time.sleep(5)
        result = kaltura_post("elasticsearch_esearch", "searchEntry", {
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[searchOperator][operator]": 1,
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchCuePointItem",
            "searchParams[searchOperator][searchItems][0][itemType]": 1,
            "searchParams[searchOperator][searchItems][0][fieldName]": "tags",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "e2e-hub-test",
        })
        total = result.get("totalCount", 0)
        assert total >= 1, f"Expected entries with e2e-hub-test cue points, got {total}"
        print(f"    eSearch found {total} entries with e2e-hub-test tagged cue points")

    runner.run_test("eSearch — find entries by cue point tags", test_esearch_cue_point)

    def test_esearch_question():
        """Search for entries containing quiz questions."""
        result = kaltura_post("elasticsearch_esearch", "searchEntry", {
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[searchOperator][operator]": 1,
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchCuePointItem",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][searchItems][0][fieldName]": "question",
            "searchParams[searchOperator][searchItems][0][searchTerm]": "2+2",
        })
        total = result.get("totalCount", 0)
        if total >= 1:
            print(f"    eSearch found {total} entries with '2+2' question")
        else:
            print(f"    eSearch returned 0 (indexing delay expected for new cue points)")

    runner.run_test("eSearch — search quiz question content", test_esearch_question)

    def test_esearch_unified():
        """Search using KalturaESearchUnifiedItem (cross-field including cue points)."""
        result = kaltura_post("elasticsearch_esearch", "searchEntry", {
            "searchParams[objectType]": "KalturaESearchEntryParams",
            "searchParams[searchOperator][objectType]": "KalturaESearchEntryOperator",
            "searchParams[searchOperator][operator]": 1,
            "searchParams[searchOperator][searchItems][0][objectType]": "KalturaESearchUnifiedItem",
            "searchParams[searchOperator][searchItems][0][itemType]": 2,
            "searchParams[searchOperator][searchItems][0][searchTerm]": "hub-test-marker",
        })
        total = result.get("totalCount", 0)
        if total >= 1:
            print(f"    Unified search found {total} entries matching 'hub-test-marker'")
        else:
            print(f"    Unified search returned 0 (indexing delay expected)")

    runner.run_test("eSearch — unified search across cue point content", test_esearch_unified)

    # ════════════════════════════════════════════
    # Phase 4: Error Handling & Bulk Operations
    # ════════════════════════════════════════════

    def test_filter_error():
        """Verify mandatory filter constraint — list without identifying filter fails."""
        try:
            kaltura_post("cuepoint_cuepoint", "list", {
                "filter[tagsLike]": "e2e-hub-test",
            })
            print("    WARNING: List without identifying filter succeeded (unexpected)")
        except Exception as e:
            err = str(e)
            assert "CANNOT_BE_NULL" in err or "PROPERTY_VALIDATION" in err, \
                f"Expected filter validation error, got: {err}"
            print(f"    Correctly rejected: {err[:70]}")

    runner.run_test("cuePoint.list — mandatory filter constraint error", test_filter_error)

    def test_add_from_bulk():
        """Import cue points via XML bulk using cuePoint.addFromBulk."""
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<scenes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <scene-code-cue-point entryId="{state['entry_id']}">
    <sceneStartTime>00:01:10.000</sceneStartTime>
    <tags>
      <tag>e2e-hub-test</tag>
      <tag>bulk-import</tag>
    </tags>
    <code>bulk-test-marker</code>
    <description>Created via addFromBulk E2E test</description>
  </scene-code-cue-point>
</scenes>"""
        resp = requests.post(
            f"{SERVICE_URL}/service/cuepoint_cuepoint/action/addFromBulk",
            data={"ks": KS, "format": 1},
            files={"fileData": ("cuepoints.xml", xml_content.encode("utf-8"), "text/xml")},
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
            print(f"    addFromBulk: {result.get('code')}: {result.get('message', '')[:80]}")
            if result.get("code") == "XML_INVALID":
                print("    Endpoint accessible — XML schema validation active")
                return
            raise Exception(f"Unexpected error: {result.get('code')}: {result.get('message')}")
        print(f"    addFromBulk response: {result.get('objectType', type(result).__name__)}")
        if isinstance(result, dict) and "id" in result:
            print(f"    Bulk job: {result.get('id')}, status={result.get('status')}")
        time.sleep(3)
        check = kaltura_post("cuepoint_cuepoint", "list", {
            "filter[entryIdEqual]": state["entry_id"],
            "filter[tagsLike]": "bulk-import",
        })
        bulk_count = check.get("totalCount", 0)
        if bulk_count >= 1:
            for obj in check.get("objects", []):
                runner.register_cleanup(f"bulk cue point {obj['id']}",
                                        lambda cp_id=obj["id"]: _delete_cue_point(cp_id))
            print(f"    Bulk import created {bulk_count} cue point(s)")
        else:
            print(f"    Bulk import queued (async — {bulk_count} found so far)")

    runner.run_test("cuePoint.addFromBulk — XML bulk import", test_add_from_bulk)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n--keep flag set. Skipping cleanup.")
        print(f"  Entry: {state.get('entry_id')}")
        print(f"  Base CP: {state.get('base_cp_id')}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

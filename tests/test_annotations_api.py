#!/usr/bin/env python3
"""End-to-end validation of the Kaltura Annotations API.

Covers: annotation CRUD, threaded parent-child, hotspot pattern,
searchableOnEntry, update, and tag-based listing.
"""

import sys
import os

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
    runner = TestRunner("Annotations — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Setup
    # ════════════════════════════════════════════

    def test_find_entry():
        entry_id, name = _find_ready_entry()
        state["entry_id"] = entry_id
        print(f"    Using entry: {entry_id} — {name}")

    runner.run_test("baseEntry.list — find READY entry", test_find_entry)

    # ════════════════════════════════════════════
    # Phase 2: Annotation CRUD
    # ════════════════════════════════════════════

    def test_annotation_add():
        """Create an annotation."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaAnnotation",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 10000,
            "cuePoint[endTime]": 20000,
            "cuePoint[text]": "E2E test annotation",
            "cuePoint[isPublic]": 1,
            "cuePoint[searchableOnEntry]": 1,
            "cuePoint[tags]": "e2e-annotation-test",
        })
        assert result.get("objectType") == "KalturaAnnotation"
        assert result.get("text") == "E2E test annotation"
        state["annotation_cp_id"] = result["id"]
        runner.register_cleanup(f"annotation {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created: {result['id']}, duration={result.get('duration')}")

    runner.run_test("cuePoint.add — create annotation", test_annotation_add)

    def test_annotation_child():
        """Create a child annotation (threaded reply)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaAnnotation",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[parentId]": state["annotation_cp_id"],
            "cuePoint[startTime]": 10000,
            "cuePoint[text]": "E2E test reply annotation",
            "cuePoint[tags]": "e2e-annotation-test",
        })
        assert result.get("parentId") == state["annotation_cp_id"]
        assert result.get("depth", 0) >= 1, f"Expected depth >= 1, got {result.get('depth')}"
        state["child_annotation_id"] = result["id"]
        runner.register_cleanup(f"child annotation {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        parent = kaltura_post("cuepoint_cuepoint", "get", {"id": state["annotation_cp_id"]})
        assert parent.get("directChildrenCount", 0) >= 1
        print(f"    Created child: {result['id']}, parent directChildren={parent.get('directChildrenCount')}")

    runner.run_test("cuePoint.add — threaded annotation (parent-child)", test_annotation_child)

    def test_annotation_update():
        """Update annotation text."""
        result = kaltura_post("cuepoint_cuepoint", "update", {
            "id": state["annotation_cp_id"],
            "cuePoint[objectType]": "KalturaAnnotation",
            "cuePoint[text]": "Updated E2E annotation text",
        })
        assert result.get("text") == "Updated E2E annotation text"
        print(f"    Updated text: {result.get('text')}")

    runner.run_test("cuePoint.update — update annotation text", test_annotation_update)

    def test_annotation_list_by_tags():
        """List annotations filtered by tags."""
        result = kaltura_post("cuepoint_cuepoint", "list", {
            "filter[entryIdEqual]": state["entry_id"],
            "filter[cuePointTypeEqual]": "annotation.Annotation",
            "filter[tagsLike]": "e2e-annotation-test",
        })
        assert result.get("totalCount", 0) >= 2, \
            f"Expected at least 2 annotations, got {result.get('totalCount')}"
        print(f"    Annotations with tag: {result.get('totalCount')}")

    runner.run_test("cuePoint.list — filter annotations by tags", test_annotation_list_by_tags)

    # ════════════════════════════════════════════
    # Phase 3: Hotspot Pattern
    # ════════════════════════════════════════════

    def test_hotspot():
        """Create a hotspot annotation (tag=hotspots with JSON partnerData)."""
        result = kaltura_post("cuepoint_cuepoint", "add", {
            "cuePoint[objectType]": "KalturaAnnotation",
            "cuePoint[entryId]": state["entry_id"],
            "cuePoint[startTime]": 5000,
            "cuePoint[endTime]": 15000,
            "cuePoint[text]": "Click for product details",
            "cuePoint[tags]": "hotspots,e2e-annotation-test",
            "cuePoint[partnerData]": '{"x":10,"y":20,"width":30,"height":25}',
        })
        assert result.get("objectType") == "KalturaAnnotation"
        assert "hotspots" in result.get("tags", ""), f"Missing hotspots tag: {result.get('tags')}"
        state["hotspot_cp_id"] = result["id"]
        runner.register_cleanup(f"hotspot {result['id']}",
                                lambda: _delete_cue_point(result["id"]))
        print(f"    Created hotspot: {result['id']}, tags={result.get('tags')}")

    runner.run_test("cuePoint.add — create hotspot annotation", test_hotspot)

    def test_searchable_on_entry():
        """Verify searchableOnEntry flag is set."""
        result = kaltura_post("cuepoint_cuepoint", "get", {"id": state["annotation_cp_id"]})
        assert result.get("searchableOnEntry") == 1, \
            f"Expected searchableOnEntry=1, got {result.get('searchableOnEntry')}"
        print(f"    searchableOnEntry={result.get('searchableOnEntry')}")

    runner.run_test("cuePoint.get — verify searchableOnEntry flag", test_searchable_on_entry)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n--keep flag set. Skipping cleanup.")
        print(f"  Entry: {state.get('entry_id')}")
        print(f"  Annotation: {state.get('annotation_cp_id')}")
        print(f"  Hotspot: {state.get('hotspot_cp_id')}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

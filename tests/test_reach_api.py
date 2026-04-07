#!/usr/bin/env python3
"""
End-to-end validation of KALTURA_REACH_API.md against the live API.

Creates a test entry, orders a REACH task, validates response shapes
and enum values, aborts the task, and cleans up.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import (
    kaltura_post, create_test_entry, delete_test_entry, TestRunner, PARTNER_ID,
)

# ── Documented enums (from KALTURA_REACH_API.md) ──

DOCUMENTED_SERVICE_FEATURES = {1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19}
DOCUMENTED_SERVICE_TYPES = {1, 2}
DOCUMENTED_OUTPUT_FORMATS = {1, 2, 3}
DOCUMENTED_TASK_STATUSES = {1, 2, 3, 4, 5, 6, 7, 8, 9}
DOCUMENTED_PROCESSING_REGIONS = {1, 2, 3}
DOCUMENTED_CONTENT_DELETION_POLICIES = {1, 2, 3, 4, 5}
DOCUMENTED_CATALOG_ITEM_STATUSES = {1, 2, 3}

# ── State shared between tests ──

state = {}


def main():
    runner = TestRunner("REACH API Validation")

    # ════════════════════════════════════════════
    # Phase 1: Catalog Discovery (read-only)
    # ════════════════════════════════════════════

    def test_catalog_list_unfiltered():
        result = kaltura_post("reach_vendorCatalogItem", "list", {
            "pager[pageSize]": 500,
        })
        assert "objects" in result, f"Missing 'objects' in response: {list(result.keys())}"
        assert "totalCount" in result, "Missing 'totalCount'"
        assert isinstance(result["totalCount"], int), f"totalCount not int: {type(result['totalCount'])}"
        assert len(result["objects"]) > 0, "No catalog items returned — is REACH enabled?"
        state["all_catalog_items"] = result["objects"]
        state["total_catalog_count"] = result["totalCount"]

    runner.run_test("vendorCatalogItem.list — unfiltered", test_catalog_list_unfiltered)

    def test_catalog_item_fields():
        required_fields = ["id", "serviceType", "serviceFeature", "sourceLanguage", "turnAroundTime", "status"]
        for item in state.get("all_catalog_items", [])[:5]:  # spot-check first 5
            for field in required_fields:
                assert field in item, f"Catalog item {item.get('id')} missing field '{field}'. Keys: {list(item.keys())}"

    runner.run_test("vendorCatalogItem — response fields match docs", test_catalog_item_fields)

    def test_catalog_filter_machine():
        result = kaltura_post("reach_vendorCatalogItem", "list", {
            "filter[serviceTypeEqual]": 2,
            "filter[statusEqual]": 2,
        })
        for item in result.get("objects", []):
            assert item["serviceType"] == 2, f"Item {item['id']} has serviceType={item['serviceType']}, expected 2 (MACHINE)"

    runner.run_test("vendorCatalogItem.list — filter serviceType=MACHINE", test_catalog_filter_machine)

    def test_catalog_filter_captions():
        result = kaltura_post("reach_vendorCatalogItem", "list", {
            "filter[serviceFeatureEqual]": 1,
            "filter[statusEqual]": 2,
        })
        for item in result.get("objects", []):
            assert item["serviceFeature"] == 1, f"Item {item['id']} has serviceFeature={item['serviceFeature']}, expected 1 (CAPTIONS)"

    runner.run_test("vendorCatalogItem.list — filter serviceFeature=CAPTIONS", test_catalog_filter_captions)

    def test_catalog_filter_english():
        """sourceLanguageEqual may not be enforced server-side; verify client-side filtering works."""
        result = kaltura_post("reach_vendorCatalogItem", "list", {
            "filter[statusEqual]": 2,
            "pager[pageSize]": 500,
        })
        english_items = [i for i in result.get("objects", []) if i.get("sourceLanguage") == "English"]
        assert len(english_items) > 0, "No English catalog items found in the full catalog"
        print(f"    Found {len(english_items)} English items out of {len(result['objects'])} total")

    runner.run_test("vendorCatalogItem.list — English items exist (client-side filter)", test_catalog_filter_english)

    def test_catalog_filter_active():
        result = kaltura_post("reach_vendorCatalogItem", "list", {
            "filter[statusEqual]": 2,
        })
        for item in result.get("objects", []):
            assert item["status"] == 2, f"Item {item['id']} has status={item['status']}, expected 2 (ACTIVE)"

    runner.run_test("vendorCatalogItem.list — filter status=ACTIVE", test_catalog_filter_active)

    def test_catalog_combined_filter():
        result = kaltura_post("reach_vendorCatalogItem", "list", {
            "filter[serviceTypeEqual]": 2,
            "filter[serviceFeatureEqual]": 1,
            "filter[statusEqual]": 2,
            "pager[pageSize]": 500,
        })
        assert result["totalCount"] > 0, "No active machine captions found"
        # Server filters serviceType/serviceFeature/status; client-filter for English
        english_items = [i for i in result["objects"]
                        if i.get("sourceLanguage") == "English"]
        assert len(english_items) > 0, "No English machine captions found after client-side filter"
        item = english_items[0]
        assert item["serviceType"] == 2
        assert item["serviceFeature"] == 1
        assert item["status"] == 2
        state["test_catalog_item_id"] = item["id"]
        state["test_catalog_item_name"] = item.get("name", "(unnamed)")
        print(f"    Using catalog item: {item['id']} — {state['test_catalog_item_name']}")

    runner.run_test("vendorCatalogItem.list — combined filter (machine+captions+English+active)", test_catalog_combined_filter)

    def test_enum_values_in_catalog():
        undocumented = {"serviceFeature": set(), "serviceType": set(), "status": set()}
        for item in state.get("all_catalog_items", []):
            sf = item.get("serviceFeature")
            if sf is not None and sf not in DOCUMENTED_SERVICE_FEATURES:
                undocumented["serviceFeature"].add(sf)
            st = item.get("serviceType")
            if st is not None and st not in DOCUMENTED_SERVICE_TYPES:
                undocumented["serviceType"].add(st)
            s = item.get("status")
            if s is not None and s not in DOCUMENTED_CATALOG_ITEM_STATUSES:
                undocumented["status"].add(s)
        for field, vals in undocumented.items():
            assert len(vals) == 0, f"Undocumented {field} values found: {vals}"

    runner.run_test("Catalog enum values — all within documented set", test_enum_values_in_catalog)

    def test_pager():
        result = kaltura_post("reach_vendorCatalogItem", "list", {
            "filter[statusEqual]": 2,
            "pager[pageSize]": 2,
            "pager[pageIndex]": 1,
        })
        assert len(result["objects"]) <= 2, f"Expected at most 2 items, got {len(result['objects'])}"
        assert result["totalCount"] >= len(result["objects"]), "totalCount inconsistent with objects"

    runner.run_test("vendorCatalogItem.list — pager behavior", test_pager)

    # ════════════════════════════════════════════
    # Phase 2: REACH Profile (read-only)
    # ════════════════════════════════════════════

    def test_reach_profile_list():
        result = kaltura_post("reach_reachProfile", "list", {
            "filter[statusEqual]": 2,
        })
        assert "objects" in result, f"Missing 'objects': {list(result.keys())}"
        assert result["totalCount"] > 0, "No active REACH profiles found"
        profile = result["objects"][0]
        required = ["id", "name", "status", "defaultOutputFormat",
                    "credit", "usedCredit", "vendorTaskProcessingRegion"]
        for field in required:
            assert field in profile, f"Profile {profile.get('id')} missing '{field}'. Keys: {list(profile.keys())}"
        state["test_reach_profile_id"] = profile["id"]
        print(f"    Using REACH profile: {profile['id']} — {profile['name']}")

    runner.run_test("reachProfile.list — active profiles with documented fields", test_reach_profile_list)

    def test_reach_profile_enums():
        result = kaltura_post("reach_reachProfile", "list", {
            "filter[statusEqual]": 2,
        })
        for profile in result.get("objects", []):
            fmt = profile.get("defaultOutputFormat")
            if fmt is not None:
                assert fmt in DOCUMENTED_OUTPUT_FORMATS, f"Undocumented outputFormat: {fmt}"
            region = profile.get("vendorTaskProcessingRegion")
            if region is not None:
                assert region in DOCUMENTED_PROCESSING_REGIONS, f"Undocumented region: {region}"
            cdp = profile.get("contentDeletionPolicy")
            if cdp is not None:
                assert cdp in DOCUMENTED_CONTENT_DELETION_POLICIES, f"Undocumented contentDeletionPolicy: {cdp}"

    runner.run_test("reachProfile — enum values match docs", test_reach_profile_enums)

    def test_reach_profile_fields():
        result = kaltura_post("reach_reachProfile", "list", {
            "filter[statusEqual]": 2,
        })
        optional_fields = [
            "enableMachineModeration", "enableHumanModeration",
            "autoDisplayMachineCaptionsOnPlayer", "autoDisplayHumanCaptionsOnPlayer",
            "enableMetadataExtraction", "enableSpeakerChangeIndication",
            "enableProfanityRemoval", "maxCharactersPerCaptionLine",
            "contentDeletionPolicy", "dictionaries", "flavorParamsIds",
        ]
        profile = result["objects"][0]
        found = [f for f in optional_fields if f in profile]
        print(f"    Profile has {len(found)}/{len(optional_fields)} optional fields documented in guide")
        # At minimum, the core config fields should be present
        assert len(found) >= 5, f"Too few documented fields present: {found}"

    runner.run_test("reachProfile — optional config fields present", test_reach_profile_fields)

    # ════════════════════════════════════════════
    # Phase 3: Task Lifecycle (creates content)
    # ════════════════════════════════════════════

    def test_create_entry():
        entry_id = create_test_entry()
        state["test_entry_id"] = entry_id
        runner.register_cleanup(f"entry {entry_id}", lambda: delete_test_entry(entry_id))
        print(f"    Created test entry: {entry_id}")
        assert entry_id, "Entry ID is empty"

    runner.run_test("Create test media entry", test_create_entry)

    def test_find_ready_entry():
        """Find an existing ready entry for task tests (media.add without content = NO_CONTENT status)."""
        result = kaltura_post("media", "list", {
            "filter[statusEqual]": 2,
            "filter[mediaTypeEqual]": 1,
            "pager[pageSize]": 1,
        })
        assert result["totalCount"] > 0, "No ready entries found in the account"
        state["ready_entry_id"] = result["objects"][0]["id"]
        print(f"    Using existing ready entry: {state['ready_entry_id']} — {result['objects'][0].get('name', '?')}")

    runner.run_test("Find existing ready entry for task tests", test_find_ready_entry)

    def test_task_add():
        if "test_catalog_item_id" not in state or "test_reach_profile_id" not in state:
            raise Exception("Skipped — missing catalog item or REACH profile from earlier tests")
        if "ready_entry_id" not in state:
            raise Exception("Skipped — no ready entry available")
        result = kaltura_post("reach_entryVendorTask", "add", {
            "entryVendorTask[objectType]": "KalturaEntryVendorTask",
            "entryVendorTask[entryId]": state["ready_entry_id"],
            "entryVendorTask[reachProfileId]": state["test_reach_profile_id"],
            "entryVendorTask[catalogItemId]": state["test_catalog_item_id"],
        })
        required = ["id", "partnerId", "entryId", "status", "reachProfileId",
                    "catalogItemId", "createdAt", "serviceType", "serviceFeature",
                    "turnAroundTime", "creationMode"]
        for field in required:
            assert field in result, f"Task response missing '{field}'. Keys: {list(result.keys())}"
        assert result["creationMode"] == 1, f"Expected creationMode=1 (MANUAL), got {result['creationMode']}"
        assert result["status"] in (1, 8), f"Expected PENDING(1) or PENDING_ENTRY_READY(8), got {result['status']}"
        state["test_task_id"] = result["id"]
        state["test_task_status"] = result["status"]
        runner.register_cleanup(f"task {result['id']}", lambda: _abort_task(result["id"]))
        print(f"    Created task: {result['id']}, status={result['status']}")

    runner.run_test("entryVendorTask.add — create machine captions task", test_task_add)

    def test_task_get():
        result = kaltura_post("reach_entryVendorTask", "get", {
            "id": state["test_task_id"],
        })
        assert result["id"] == state["test_task_id"], f"Task ID mismatch: {result['id']} != {state['test_task_id']}"
        assert result["status"] in DOCUMENTED_TASK_STATUSES, f"Undocumented status: {result['status']}"

    runner.run_test("entryVendorTask.get — retrieve created task", test_task_get)

    def test_task_list_by_entry():
        result = kaltura_post("reach_entryVendorTask", "list", {
            "filter[entryIdEqual]": state["ready_entry_id"],
        })
        assert result["totalCount"] >= 1, f"Expected at least 1 task, got {result['totalCount']}"
        task_ids = [t["id"] for t in result["objects"]]
        assert state["test_task_id"] in task_ids, f"Task {state['test_task_id']} not in list: {task_ids}"

    runner.run_test("entryVendorTask.list — filter by entryId", test_task_list_by_entry)

    def test_task_list_by_status():
        result = kaltura_post("reach_entryVendorTask", "list", {
            "filter[entryIdEqual]": state["ready_entry_id"],
            "filter[statusIn]": "1,8",
        })
        task_ids = [t["id"] for t in result.get("objects", [])]
        assert state["test_task_id"] in task_ids, f"Task {state['test_task_id']} not in status-filtered list"

    runner.run_test("entryVendorTask.list — filter by statusIn", test_task_list_by_status)

    def test_task_list_by_catalog_item():
        result = kaltura_post("reach_entryVendorTask", "list", {
            "filter[entryIdEqual]": state["ready_entry_id"],
            "filter[catalogItemIdEqual]": state["test_catalog_item_id"],
        })
        task_ids = [t["id"] for t in result.get("objects", [])]
        assert state["test_task_id"] in task_ids, f"Task not in catalog-filtered list"

    runner.run_test("entryVendorTask.list — filter by catalogItemId", test_task_list_by_catalog_item)

    def test_task_abort():
        result = kaltura_post("reach_entryVendorTask", "abort", {
            "id": state["test_task_id"],
        })
        assert result["status"] == 7, f"Expected ABORTED(7), got {result['status']}"

    runner.run_test("entryVendorTask.abort — cancel the task", test_task_abort)

    def test_task_confirm_aborted():
        """After abort, the task may be deleted entirely (returns ENTRY_VENDOR_TASK_NOT_FOUND)
        or may still exist with status=7. Both behaviors are valid."""
        try:
            result = kaltura_post("reach_entryVendorTask", "get", {
                "id": state["test_task_id"],
            })
            assert result["status"] == 7, f"Expected ABORTED(7) after abort, got {result['status']}"
            print("    Task still exists with status=7 (ABORTED)")
        except Exception as e:
            if "ENTRY_VENDOR_TASK_NOT_FOUND" in str(e):
                print("    Task was deleted after abort (ENTRY_VENDOR_TASK_NOT_FOUND) — expected behavior")
            else:
                raise

    runner.run_test("entryVendorTask.get — confirm task gone or aborted after abort", test_task_confirm_aborted)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    runner.cleanup()
    success = runner.summary()
    sys.exit(0 if success else 1)


def _abort_task(task_id):
    """Best-effort abort for cleanup. Ignores errors (task may already be aborted)."""
    try:
        kaltura_post("reach_entryVendorTask", "abort", {"id": task_id})
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA REACH API — End-to-End Validation")
    print(f"{'='*60}\n")
    main()

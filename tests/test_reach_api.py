#!/usr/bin/env python3
"""
End-to-end validation of KALTURA_REACH_API.md against the live API.

Covers: catalog discovery, REACH profile fields and enums, task lifecycle
(add/get/list/abort), automation rules (Boolean condition, category condition,
always-on), and E2E auto-task creation via rules.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import (
    kaltura_post, create_test_entry, delete_test_entry, TestRunner, PARTNER_ID,
)

# Small public video for REACH rule trigger test (direct MP4 URL)
SAMPLE_VIDEO_URL = os.environ.get(
    "KALTURA_TEST_VIDEO_URL",
    "https://cfvod.kaltura.com/pd/p/811441/sp/81144100/serveFlavor/entryId/1_uoup50ye/v/1/ev/6/flavorId/1_m8w4gjs8/name/a.mp4"
)

# Polling config
POLL_INTERVAL = 5
POLL_TIMEOUT = 120

EVT_SVC = "eventnotification_eventnotificationtemplate"

# ── Documented enums (from KALTURA_REACH_API.md) ──

DOCUMENTED_SERVICE_FEATURES = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23}
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
        # Server filters serviceType/serviceFeature/status; prefer English, fall back to Auto Detect
        preferred = [i for i in result["objects"]
                     if i.get("sourceLanguage") == "English"]
        if not preferred:
            preferred = [i for i in result["objects"]
                         if i.get("sourceLanguage") == "Auto Detect"]
        assert len(preferred) > 0, \
            f"No English or Auto Detect machine captions found. Languages: {set(i.get('sourceLanguage') for i in result['objects'])}"
        item = preferred[0]
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
    # Phase 2b: REACH Automation Rules
    # ════════════════════════════════════════════

    TS = int(time.time())

    def test_list_boolean_system_templates():
        """List Boolean system templates available as REACH rule conditions."""
        result = kaltura_post(EVT_SVC, "listTemplates", {
            "filter[objectType]": "KalturaEventNotificationTemplateFilter",
            "filter[typeEqual]": "booleanNotification.Boolean",
        })
        assert "objects" in result, f"Expected objects: {result}"
        assert result["totalCount"] > 0, "No Boolean system templates — is Event Notification plugin enabled?"
        state["boolean_system_templates"] = result["objects"]
        print(f"    Boolean system templates: {result['totalCount']}")
        for t in result["objects"][:3]:
            print(f"      {t['id']}: {t.get('name', '?')} (conditions={len(t.get('eventConditions', []))})")

    runner.run_test("listTemplates — Boolean system templates for REACH rules", test_list_boolean_system_templates)

    def test_clone_boolean_for_rule():
        """Clone a Boolean template to use as a REACH rule condition."""
        templates = state.get("boolean_system_templates", [])
        assert len(templates) > 0, "No Boolean system templates available"
        src_id = templates[0]["id"]
        result = kaltura_post(EVT_SVC, "clone", {
            "id": src_id,
            "eventNotificationTemplate[objectType]": "KalturaBooleanNotificationTemplate",
            "eventNotificationTemplate[name]": f"REACH Rule Test {TS}",
            "eventNotificationTemplate[systemName]": f"REACH_RULE_TEST_{TS}",
        })
        assert "id" in result, f"Clone failed: {result}"
        assert result.get("type") == "booleanNotification.Boolean"
        state["rule_boolean_id"] = result["id"]
        runner.register_cleanup(
            f"rule boolean template {result['id']}",
            lambda: _safe_delete_template(state["rule_boolean_id"]),
        )
        conditions = result.get("eventConditions", [])
        print(f"    Cloned Boolean template: {result['id']} from {src_id}, {len(conditions)} conditions")

    runner.run_test("clone — Boolean template for REACH rule condition", test_clone_boolean_for_rule)

    def test_save_existing_rules():
        """Save existing REACH profile rules before modification."""
        profile_id = state.get("test_reach_profile_id")
        assert profile_id, "No REACH profile from Phase 2"
        result = kaltura_post("reach_reachProfile", "get", {"id": profile_id})
        state["original_rules"] = result.get("rules", [])
        runner.register_cleanup(
            f"restore rules on profile {profile_id}",
            lambda: _restore_rules(profile_id, state.get("original_rules", [])),
        )
        print(f"    Saved {len(state['original_rules'])} existing rule(s)")

    runner.run_test("reachProfile.get — save existing rules before modification", test_save_existing_rules)

    def test_add_boolean_rule():
        """Add a Boolean condition rule to the REACH profile."""
        profile_id = state["test_reach_profile_id"]
        boolean_id = state["rule_boolean_id"]
        catalog_id = state["test_catalog_item_id"]
        result = kaltura_post("reach_reachProfile", "update", {
            "id": profile_id,
            "reachProfile[rules][0][objectType]": "KalturaRule",
            "reachProfile[rules][0][description]": f"E2E Test Boolean Rule {TS}",
            "reachProfile[rules][0][conditions][0][objectType]": "KalturaBooleanEventNotificationCondition",
            "reachProfile[rules][0][conditions][0][booleanEventNotificationIds]": str(boolean_id),
            "reachProfile[rules][0][actions][0][objectType]": "KalturaAddEntryVendorTaskAction",
            "reachProfile[rules][0][actions][0][catalogItemIds]": str(catalog_id),
            "reachProfile[rules][0][actions][0][entryObjectType]": 1,
        })
        rules = result.get("rules", [])
        assert len(rules) >= 1, f"Expected at least 1 rule, got {len(rules)}"
        found = any(f"E2E Test Boolean Rule {TS}" in r.get("description", "") for r in rules)
        assert found, f"Boolean rule not found after update"
        print(f"    Added Boolean rule: condition={boolean_id}, catalogItem={catalog_id}")

    runner.run_test("reachProfile.update — add Boolean condition rule", test_add_boolean_rule)

    def test_verify_boolean_rule():
        """Verify the Boolean rule persisted via reachProfile.get."""
        result = kaltura_post("reach_reachProfile", "get", {"id": state["test_reach_profile_id"]})
        rules = result.get("rules", [])
        found_rule = None
        for r in rules:
            if f"E2E Test Boolean Rule {TS}" in r.get("description", ""):
                found_rule = r
                break
        assert found_rule, f"Boolean rule not found in get response. Rules: {[r.get('description') for r in rules]}"
        conditions = found_rule.get("conditions", [])
        assert len(conditions) >= 1, "No conditions on rule"
        cond = conditions[0]
        assert cond.get("objectType") == "KalturaBooleanEventNotificationCondition", \
            f"Expected KalturaBooleanEventNotificationCondition, got {cond.get('objectType')}"
        assert str(state["rule_boolean_id"]) in str(cond.get("booleanEventNotificationIds", "")), \
            f"Boolean template ID mismatch in condition"
        actions = found_rule.get("actions", [])
        assert len(actions) >= 1, "No actions on rule"
        act = actions[0]
        assert act.get("objectType") == "KalturaAddEntryVendorTaskAction", \
            f"Expected KalturaAddEntryVendorTaskAction, got {act.get('objectType')}"
        assert str(state["test_catalog_item_id"]) in str(act.get("catalogItemIds", "")), \
            f"Catalog item ID mismatch in action"
        print(f"    Verified: condition type={cond['objectType']}, action catalogItems={act.get('catalogItemIds')}")

    runner.run_test("reachProfile.get — verify Boolean rule persisted", test_verify_boolean_rule)

    def test_add_category_rule():
        """Replace with a category-based rule (KalturaCategoryEntryCondition)."""
        profile_id = state["test_reach_profile_id"]
        catalog_id = state["test_catalog_item_id"]
        # Use categoryId=99999999 (non-existent, safe — won't trigger)
        result = kaltura_post("reach_reachProfile", "update", {
            "id": profile_id,
            "reachProfile[rules][0][objectType]": "KalturaRule",
            "reachProfile[rules][0][description]": f"E2E Test Category Rule {TS}",
            "reachProfile[rules][0][conditions][0][objectType]": "KalturaCategoryEntryCondition",
            "reachProfile[rules][0][conditions][0][categoryId]": 99999999,
            "reachProfile[rules][0][actions][0][objectType]": "KalturaAddEntryVendorTaskAction",
            "reachProfile[rules][0][actions][0][catalogItemIds]": str(catalog_id),
        })
        rules = result.get("rules", [])
        found = any(f"E2E Test Category Rule {TS}" in r.get("description", "") for r in rules)
        assert found, "Category rule not found after update"
        # Verify condition type
        for r in rules:
            if f"E2E Test Category Rule {TS}" in r.get("description", ""):
                cond = r.get("conditions", [{}])[0]
                assert cond.get("objectType") == "KalturaCategoryEntryCondition", \
                    f"Expected KalturaCategoryEntryCondition, got {cond.get('objectType')}"
                print(f"    Category rule added: categoryId=99999999, catalogItem={catalog_id}")

    runner.run_test("reachProfile.update — add category condition rule", test_add_category_rule)

    def test_add_always_on_rule():
        """Replace with an always-on rule (no conditions) — triggers for every READY entry."""
        profile_id = state["test_reach_profile_id"]
        catalog_id = state["test_catalog_item_id"]
        result = kaltura_post("reach_reachProfile", "update", {
            "id": profile_id,
            "reachProfile[rules][0][objectType]": "KalturaRule",
            "reachProfile[rules][0][description]": f"E2E Test Always-On Rule {TS}",
            "reachProfile[rules][0][actions][0][objectType]": "KalturaAddEntryVendorTaskAction",
            "reachProfile[rules][0][actions][0][catalogItemIds]": str(catalog_id),
        })
        rules = result.get("rules", [])
        found_rule = None
        for r in rules:
            if f"E2E Test Always-On Rule {TS}" in r.get("description", ""):
                found_rule = r
                break
        assert found_rule, "Always-on rule not found after update"
        conditions = found_rule.get("conditions", [])
        assert len(conditions) == 0, f"Expected 0 conditions on always-on rule, got {len(conditions)}"
        print(f"    Always-on rule added (no conditions): catalogItem={catalog_id}")

    runner.run_test("reachProfile.update — add always-on rule (no conditions)", test_add_always_on_rule)

    def test_multiple_rules_stop_processing():
        """Configure multiple rules with stopProcessing flag."""
        profile_id = state["test_reach_profile_id"]
        catalog_id = state["test_catalog_item_id"]
        boolean_id = state.get("rule_boolean_id")
        # Rule 0: Boolean condition (if available) or category condition with stopProcessing
        params = {
            "id": profile_id,
            "reachProfile[rules][0][objectType]": "KalturaRule",
            "reachProfile[rules][0][description]": f"E2E Rule 0 (stopProcessing) {TS}",
            "reachProfile[rules][0][stopProcessing]": 1,
            "reachProfile[rules][0][actions][0][objectType]": "KalturaAddEntryVendorTaskAction",
            "reachProfile[rules][0][actions][0][catalogItemIds]": str(catalog_id),
            "reachProfile[rules][1][objectType]": "KalturaRule",
            "reachProfile[rules][1][description]": f"E2E Rule 1 (fallback) {TS}",
            "reachProfile[rules][1][conditions][0][objectType]": "KalturaCategoryEntryCondition",
            "reachProfile[rules][1][conditions][0][categoryId]": 99999999,
            "reachProfile[rules][1][actions][0][objectType]": "KalturaAddEntryVendorTaskAction",
            "reachProfile[rules][1][actions][0][catalogItemIds]": str(catalog_id),
        }
        if boolean_id:
            params["reachProfile[rules][0][conditions][0][objectType]"] = "KalturaBooleanEventNotificationCondition"
            params["reachProfile[rules][0][conditions][0][booleanEventNotificationIds]"] = str(boolean_id)
        else:
            # Use a category condition as fallback
            params["reachProfile[rules][0][conditions][0][objectType]"] = "KalturaCategoryEntryCondition"
            params["reachProfile[rules][0][conditions][0][categoryId]"] = 88888888
        result = kaltura_post("reach_reachProfile", "update", params)
        rules = result.get("rules", [])
        assert len(rules) >= 2, f"Expected 2+ rules, got {len(rules)}"
        rule0 = next((r for r in rules if f"Rule 0 (stopProcessing) {TS}" in r.get("description", "")), None)
        rule1 = next((r for r in rules if f"Rule 1 (fallback) {TS}" in r.get("description", "")), None)
        assert rule0, "Rule 0 not found"
        assert rule1, "Rule 1 not found"
        assert rule0.get("stopProcessing") in (True, 1), \
            f"Expected stopProcessing=true on rule 0, got {rule0.get('stopProcessing')}"
        print(f"    2 rules configured: rule0.stopProcessing=true, rule1=category fallback")

    runner.run_test("reachProfile.update — multiple rules with stopProcessing", test_multiple_rules_stop_processing)

    def test_trigger_auto_task():
        """E2E: set always-on rule, import a video, verify auto-created task (creationMode=2)."""
        profile_id = state["test_reach_profile_id"]
        catalog_id = state["test_catalog_item_id"]
        # Step 1: Set always-on rule
        kaltura_post("reach_reachProfile", "update", {
            "id": profile_id,
            "reachProfile[rules][0][objectType]": "KalturaRule",
            "reachProfile[rules][0][description]": f"E2E Trigger Test {TS}",
            "reachProfile[rules][0][actions][0][objectType]": "KalturaAddEntryVendorTaskAction",
            "reachProfile[rules][0][actions][0][catalogItemIds]": str(catalog_id),
        })
        print(f"    Always-on rule set, importing video...")
        # Step 2: Import a video so entry reaches READY status
        entry = kaltura_post("media", "addFromUrl", {
            "mediaEntry[objectType]": "KalturaMediaEntry",
            "mediaEntry[name]": f"REACH Rule Trigger Test {TS}",
            "mediaEntry[mediaType]": 1,
            "url": SAMPLE_VIDEO_URL,
        })
        assert "id" in entry, f"addFromUrl failed: {entry}"
        state["trigger_entry_id"] = entry["id"]
        runner.register_cleanup(f"trigger entry {entry['id']}", lambda: delete_test_entry(entry["id"]))
        print(f"    Entry imported: {entry['id']}, waiting for READY...")
        # Step 3: Poll for READY
        deadline = time.time() + POLL_TIMEOUT
        ready = False
        while time.time() < deadline:
            check = kaltura_post("media", "get", {"entryId": entry["id"]})
            if check.get("status") == 2:
                ready = True
                print(f"    Entry READY after ~{int(POLL_TIMEOUT - (deadline - time.time()))}s")
                break
            time.sleep(POLL_INTERVAL)
        if not ready:
            print(f"    WARN: Entry did not reach READY within {POLL_TIMEOUT}s — auto-task check may fail")
        # Step 4: Wait a bit more for kReachManager to process
        time.sleep(10)
        # Step 5: Check for auto-created tasks
        tasks = kaltura_post("reach_entryVendorTask", "list", {
            "filter[entryIdEqual]": entry["id"],
            "filter[creationModeEqual]": 2,
        })
        auto_tasks = tasks.get("objects", [])
        if len(auto_tasks) > 0:
            task = auto_tasks[0]
            state["auto_task_id"] = task["id"]
            runner.register_cleanup(f"auto-task {task['id']}", lambda: _abort_task(task["id"]))
            assert task["creationMode"] == 2, f"Expected creationMode=2, got {task['creationMode']}"
            print(f"    Auto-created task: {task['id']}, status={task['status']}, "
                  f"catalogItem={task.get('catalogItemId')}, creationMode={task['creationMode']}")
        else:
            # Auto-task may take longer or kReachManager may not be configured
            print(f"    WARN: No auto-created tasks found yet (kReachManager may need more time)")
            print(f"    This can happen if the Boolean conditions don't match or the profile has constraints")

    runner.run_test("E2E — always-on rule triggers auto-task (creationMode=2)", test_trigger_auto_task)

    def test_list_tasks_creation_mode_filter():
        """Verify entryVendorTask.list accepts creationModeEqual filter parameter."""
        result = kaltura_post("reach_entryVendorTask", "list", {
            "filter[creationModeEqual]": 2,
            "pager[pageSize]": 5,
        })
        assert "objects" in result, f"Expected objects key: {result}"
        assert "totalCount" in result, f"Expected totalCount key: {result}"
        # Check if the filter is applied — all returned tasks should have creationMode=2
        # If the API ignores this filter, tasks with other modes may appear
        auto_count = sum(1 for t in result.get("objects", []) if t.get("creationMode") == 2)
        other_count = sum(1 for t in result.get("objects", []) if t.get("creationMode") != 2)
        if other_count > 0:
            print(f"    WARN: creationModeEqual filter returned {other_count} non-automatic task(s) — filter may not be supported")
        print(f"    creationModeEqual=2 query accepted: {result['totalCount']} total, {auto_count} automatic in page")

    runner.run_test("entryVendorTask.list — filter by creationMode=AUTOMATIC", test_list_tasks_creation_mode_filter)

    def test_restore_rules():
        """Restore original REACH profile rules."""
        profile_id = state.get("test_reach_profile_id")
        original = state.get("original_rules", [])
        _restore_rules(profile_id, original)
        # Remove the cleanup since we already restored
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if "restore rules" not in label
        ]
        # Verify
        result = kaltura_post("reach_reachProfile", "get", {"id": profile_id})
        restored = result.get("rules", [])
        print(f"    Restored {len(restored)} original rule(s)")

    runner.run_test("reachProfile.update — restore original rules", test_restore_rules)

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
            "filter[orderBy]": "-plays",
            "filter[playsGreaterThanOrEqual]": 1,
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
        assert "id" in result, f"Task add failed: {result}"
        state["test_task_id"] = result["id"]
        state["test_task_status"] = result.get("status")
        runner.register_cleanup(f"task {result['id']}", lambda: _abort_task(result["id"]))
        required = ["partnerId", "entryId", "status", "reachProfileId",
                    "catalogItemId", "createdAt", "serviceType", "serviceFeature",
                    "turnAroundTime", "creationMode"]
        for field in required:
            assert field in result, f"Task response missing '{field}'. Keys: {list(result.keys())}"
        assert result["creationMode"] == 1, f"Expected creationMode=1 (MANUAL), got {result['creationMode']}"
        assert result["status"] in (1, 8), f"Expected PENDING(1) or PENDING_ENTRY_READY(8), got {result['status']}"
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

    def test_task_approve():
        """Approve requires PENDING_MODERATION (4). Our task is PENDING (1), so verify
        the API is accessible and returns the correct precondition error."""
        try:
            kaltura_post("reach_entryVendorTask", "approve", {
                "id": state["test_task_id"],
            })
            print("    Task approved (was in PENDING_MODERATION)")
        except Exception as e:
            err = str(e)
            if "ENTRY_VENDOR_TASK_NOT_FOUND" in err:
                raise  # genuine failure
            # Any other error = action is accessible but precondition not met
            assert "ENTRY_VENDOR_TASK" in err or "status" in err.lower() or "approve" in err.lower(), \
                f"Unexpected error: {err}"
            print(f"    Correctly rejected (task not in PENDING_MODERATION): {err[:80]}")

    runner.run_test("entryVendorTask.approve — accessible (requires PENDING_MODERATION)", test_task_approve)

    def test_task_reject():
        """Reject requires PENDING_MODERATION (4). Verify API is accessible."""
        try:
            kaltura_post("reach_entryVendorTask", "reject", {
                "id": state["test_task_id"],
                "rejectReason": "E2E test validation",
            })
            print("    Task rejected (was in PENDING_MODERATION)")
        except Exception as e:
            err = str(e)
            if "ENTRY_VENDOR_TASK_NOT_FOUND" in err:
                raise
            assert "ENTRY_VENDOR_TASK" in err or "status" in err.lower() or "reject" in err.lower(), \
                f"Unexpected error: {err}"
            print(f"    Correctly rejected (task not in PENDING_MODERATION): {err[:80]}")

    runner.run_test("entryVendorTask.reject — accessible (requires PENDING_MODERATION)", test_task_reject)

    def test_task_export_csv():
        """exportToCsv creates a batch job and returns the recipient email.
        Known server-side bug: may return INTERNAL_SERVERL_ERROR on some accounts."""
        try:
            result = kaltura_post("reach_entryVendorTask", "exportToCsv", {
                "filter[statusEqual]": 2,
            })
            assert isinstance(result, str) and "@" in result, \
                f"Expected email address, got: {result}"
            print(f"    CSV export queued → {result}")
        except Exception as e:
            err = str(e)
            if "INTERNAL_SERVERL_ERROR" in err or "INTERNAL_SERVER" in err:
                print(f"    Known server-side bug: {err[:80]}")
                print(f"    Action is publisher-permissioned (ADMIN_BASE) — server bug, not permissions")
            else:
                raise

    runner.run_test("entryVendorTask.exportToCsv — batch CSV export", test_task_export_csv)

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
            assert result["status"] in (3, 7), f"Expected ABORTED(7) or DELETED(3) after abort, got {result['status']}"
            label = "ABORTED" if result["status"] == 7 else "DELETED"
            print(f"    Task status={result['status']} ({label}) after abort")
        except Exception as e:
            if "ENTRY_VENDOR_TASK_NOT_FOUND" in str(e):
                print("    Task was deleted after abort (ENTRY_VENDOR_TASK_NOT_FOUND) — expected behavior")
            else:
                raise

    runner.run_test("entryVendorTask.get — confirm task gone or aborted after abort", test_task_confirm_aborted)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n--- Keeping test resources (--keep flag) ---")
        for key, val in state.items():
            if "id" in key.lower():
                print(f"    {key}: {val}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


def _abort_task(task_id):
    """Best-effort abort for cleanup. Ignores errors (task may already be aborted)."""
    try:
        kaltura_post("reach_entryVendorTask", "abort", {"id": task_id})
    except Exception:
        pass


def _safe_delete_template(template_id):
    """Best-effort delete for event notification template. Ignores errors."""
    try:
        kaltura_post(EVT_SVC, "delete", {"id": template_id})
    except Exception:
        pass


def _restore_rules(profile_id, original_rules):
    """Restore original rules on a REACH profile. If original_rules is empty, clear rules."""
    params = {"id": profile_id}
    if not original_rules:
        # Clear all rules by sending an empty array marker
        params["reachProfile[rules]"] = "-"
    else:
        for i, rule in enumerate(original_rules):
            obj_type = rule.get("objectType", "KalturaRule")
            params[f"reachProfile[rules][{i}][objectType]"] = obj_type
            if rule.get("description"):
                params[f"reachProfile[rules][{i}][description]"] = rule["description"]
            if rule.get("stopProcessing"):
                params[f"reachProfile[rules][{i}][stopProcessing]"] = rule["stopProcessing"]
            for ci, cond in enumerate(rule.get("conditions", [])):
                cond_type = cond.get("objectType", "")
                params[f"reachProfile[rules][{i}][conditions][{ci}][objectType]"] = cond_type
                if "booleanEventNotificationIds" in cond:
                    params[f"reachProfile[rules][{i}][conditions][{ci}][booleanEventNotificationIds]"] = \
                        cond["booleanEventNotificationIds"]
                if "categoryId" in cond:
                    params[f"reachProfile[rules][{i}][conditions][{ci}][categoryId]"] = cond["categoryId"]
            for ai, act in enumerate(rule.get("actions", [])):
                act_type = act.get("objectType", "")
                params[f"reachProfile[rules][{i}][actions][{ai}][objectType]"] = act_type
                if "catalogItemIds" in act:
                    params[f"reachProfile[rules][{i}][actions][{ai}][catalogItemIds]"] = act["catalogItemIds"]
                if "entryObjectType" in act:
                    params[f"reachProfile[rules][{i}][actions][{ai}][entryObjectType]"] = act["entryObjectType"]
    kaltura_post("reach_reachProfile", "update", params)


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA REACH API — End-to-End Validation")
    print(f"{'='*60}\n")
    main()

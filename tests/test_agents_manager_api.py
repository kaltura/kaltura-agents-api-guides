#!/usr/bin/env python3
"""
End-to-end validation of KALTURA_AGENTS_MANAGER_API.md against the live API.

Creates a test agent (trigger + actions + agent), validates response shapes,
verifies listing and cross-references with REACH catalog items, then cleans up.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import (
    kaltura_post, agents_post, TestRunner, PARTNER_ID,
)

state = {}

REACH_PROFILE_ID = None  # populated dynamically


def main():
    runner = TestRunner("Agents Manager API Validation")

    # ════════════════════════════════════════════
    # Pre-flight: Auth check
    # ════════════════════════════════════════════

    def test_auth():
        result = agents_post("/api/v1/agent/list", {"partnerId": PARTNER_ID})
        assert "objects" in result, f"Unexpected response: {result}"

    runner.run_test("Pre-flight auth check", test_auth)

    if not runner.results[-1][1]:
        runner.cleanup()
        runner.summary()
        sys.exit(1)

    # ════════════════════════════════════════════
    # Phase 1: Action Definitions (read-only)
    # ════════════════════════════════════════════

    def test_action_definition_list():
        result = agents_post("/api/v1/actionDefinition/list", {"partnerId": PARTNER_ID})
        assert "totalCount" in result, f"Missing 'totalCount'. Keys: {list(result.keys())}"
        assert "objects" in result, f"Missing 'objects'. Keys: {list(result.keys())}"
        assert isinstance(result["totalCount"], int)
        assert len(result["objects"]) > 0, "No action definitions returned"
        state["action_definitions"] = result["objects"]
        types = [d["type"] for d in result["objects"]]
        print(f"    Found {len(result['objects'])} action definitions: {types}")

    runner.run_test("actionDefinition/list — basic response shape", test_action_definition_list)

    def test_action_definition_fields():
        required_fields = ["objectType", "type"]
        for defn in state.get("action_definitions", []):
            for field in required_fields:
                assert field in defn, (
                    f"Action definition missing '{field}'. Keys: {list(defn.keys())}"
                )
            # All definitions should have tags
            assert "tags" in defn, f"Definition type={defn['type']} missing 'tags'"

    runner.run_test("actionDefinition — response fields (objectType, type, tags)", test_action_definition_fields)

    def test_action_definition_types():
        """Verify known action types exist."""
        types = {d["type"] for d in state.get("action_definitions", [])}
        # At minimum captions should exist
        assert "captions" in types, f"'captions' not in action types: {types}"
        print(f"    Available types: {sorted(types)}")

    runner.run_test("actionDefinition — known action types present", test_action_definition_types)

    def test_captions_definition_structure():
        """Captions action definition has vendors with languages and catalogItemIds."""
        captions_def = None
        for d in state.get("action_definitions", []):
            if d["type"] == "captions":
                captions_def = d
                break
        assert captions_def is not None, "No captions definition found"
        assert "vendors" in captions_def or "catalogItems" in captions_def, (
            f"Captions definition missing 'vendors' or 'catalogItems'. Keys: {list(captions_def.keys())}"
        )
        # Extract a catalogItemId for later tests
        if "vendors" in captions_def:
            for vendor in captions_def["vendors"]:
                for lang in vendor.get("languages", []):
                    if lang.get("language") == "English":
                        state["test_catalog_item_id"] = lang["catalogItemId"]
                        state["test_vendor_name"] = vendor.get("name", "?")
                        print(f"    Using: vendor={state['test_vendor_name']}, "
                              f"catalogItemId={state['test_catalog_item_id']}, language=English")
                        return
        # Fallback: use catalogItems if present
        if "catalogItems" in captions_def:
            for item in captions_def["catalogItems"]:
                state["test_catalog_item_id"] = item.get("catalogItemId") or item.get("id")
                print(f"    Using catalogItemId={state['test_catalog_item_id']} from catalogItems")
                return
        raise Exception("Could not extract a catalogItemId from captions definition")

    runner.run_test("actionDefinition — captions has vendors/languages/catalogItemIds", test_captions_definition_structure)

    def test_reach_profile_from_definitions():
        """Extract REACH profile ID from action definitions."""
        global REACH_PROFILE_ID
        for d in state.get("action_definitions", []):
            for rp in d.get("reachProfiles", []):
                if rp.get("id") is not None:
                    REACH_PROFILE_ID = rp["id"]
                    print(f"    Using REACH profile: {REACH_PROFILE_ID} — {rp.get('name', '?')}")
                    return
        raise Exception("No REACH profile with a valid ID found in action definitions")

    runner.run_test("actionDefinition — REACH profile ID available", test_reach_profile_from_definitions)

    def test_catalog_item_cross_reference():
        """Verify catalogItemId from Agents Manager exists in REACH."""
        catalog_id = state["test_catalog_item_id"]
        result = kaltura_post("reach_vendorCatalogItem", "list", {
            "filter[idEqual]": catalog_id,
        })
        assert result["totalCount"] >= 1, (
            f"catalogItemId {catalog_id} from Agents Manager not found in REACH"
        )
        item = result["objects"][0]
        print(f"    Confirmed in REACH: {item.get('name', '?')}, "
              f"serviceFeature={item.get('serviceFeature')}, serviceType={item.get('serviceType')}")

    runner.run_test("catalogItemId cross-reference — Agents Manager → REACH", test_catalog_item_cross_reference)

    # ════════════════════════════════════════════
    # Phase 2: Create Trigger
    # ════════════════════════════════════════════

    def test_trigger_create():
        result = agents_post("/api/v1/trigger/create", {
            "partnerId": PARTNER_ID,
            "systemName": "RUN_ON_DEMAND",
            "triggerParameters": {},
        })
        assert "id" in result, f"Trigger create response missing 'id'. Keys: {list(result.keys())}"
        assert result.get("systemName") == "RUN_ON_DEMAND"
        assert "executionParameters" in result, "Missing executionParameters (auto-generated)"
        state["test_trigger_id"] = result["id"]
        runner.register_cleanup(f"trigger {result['id']}",
                                lambda: _safe_delete("trigger", result["id"]))
        print(f"    Created trigger: {result['id']} (systemName={result['systemName']})")

    runner.run_test("trigger/create — RUN_ON_DEMAND", test_trigger_create)

    def test_trigger_fields():
        """Verify trigger response has documented fields."""
        result = agents_post("/api/v1/trigger/list", {"partnerId": PARTNER_ID})
        assert result["totalCount"] > 0
        # Find our trigger
        test_trigger = None
        for t in result["objects"]:
            if t["id"] == state.get("test_trigger_id"):
                test_trigger = t
                break
        assert test_trigger is not None, "Test trigger not in list"
        required = ["id", "partnerId", "status", "systemName", "executionParameters"]
        for field in required:
            assert field in test_trigger, f"Trigger missing '{field}'. Keys: {list(test_trigger.keys())}"

    runner.run_test("trigger/list — trigger has documented fields", test_trigger_fields)

    # ════════════════════════════════════════════
    # Phase 3: Create Actions
    # ════════════════════════════════════════════

    def test_actions_create():
        payload = {
            "partnerId": PARTNER_ID,
            "workflowId": "publishing_workflow_dag",
            "workflowActions": [
                {
                    "reach_profile_id": REACH_PROFILE_ID,
                    "type": "captions",
                    "catalog_item_id": state["test_catalog_item_id"],
                },
            ],
        }
        result = agents_post("/api/v1/actions/create", payload)
        assert "id" in result, f"Actions create response missing 'id'. Keys: {list(result.keys())}"
        assert result.get("workflowId") == "publishing_workflow_dag"
        assert len(result.get("workflowActions", [])) == 1
        state["test_actions_id"] = result["id"]
        runner.register_cleanup(f"actions {result['id']}",
                                lambda: _safe_delete("actions", result["id"]))
        print(f"    Created actions: {result['id']} (workflowId={result['workflowId']})")

    runner.run_test("actions/create — with workflowId and workflowActions", test_actions_create)

    # ════════════════════════════════════════════
    # Phase 4: Create & Validate Agent
    # ════════════════════════════════════════════

    def test_agent_create():
        ts = int(time.time())
        payload = {
            "partnerId": PARTNER_ID,
            "name": f"API_DOC_VALIDATION_TEST_{ts}",
            "description": "Temporary agent for API doc validation. Safe to delete.",
            "triggerId": state["test_trigger_id"],
            "actionsId": state["test_actions_id"],
            "status": "Disabled",
        }
        result = agents_post("/api/v1/agent/create", payload)
        assert "id" in result, f"Agent create response missing 'id'. Keys: {list(result.keys())}"
        # Agent create returns inline trigger and actions objects
        assert "trigger" in result, "Agent create response missing inline 'trigger'"
        assert "actions" in result, "Agent create response missing inline 'actions'"
        assert result["trigger"]["id"] == state["test_trigger_id"]
        assert result["actions"]["id"] == state["test_actions_id"]
        state["test_agent_id"] = result["id"]
        runner.register_cleanup(f"agent {result['id']}",
                                lambda: _safe_delete("agent", result["id"]))
        print(f"    Created agent: {result['id']} — {result['name']}, status={result['status']}")

    runner.run_test("agent/create — returns inline trigger and actions", test_agent_create)

    def test_agent_list():
        result = agents_post("/api/v1/agent/list", {"partnerId": PARTNER_ID})
        assert "objects" in result
        assert "totalCount" in result
        agent_ids = [a["id"] for a in result["objects"]]
        assert state["test_agent_id"] in agent_ids, (
            f"Test agent {state['test_agent_id']} not found in list"
        )
        print(f"    Agent list: {result['totalCount']} total, test agent found")

    runner.run_test("agent/list — test agent appears", test_agent_list)

    def test_agent_list_fields():
        """Agent list returns triggerId and actionsId as strings (not inline objects)."""
        result = agents_post("/api/v1/agent/list", {"partnerId": PARTNER_ID})
        test_agent = None
        for a in result["objects"]:
            if a["id"] == state["test_agent_id"]:
                test_agent = a
                break
        assert test_agent is not None
        required = ["id", "name", "status", "triggerId", "actionsId", "partnerId"]
        for field in required:
            assert field in test_agent, f"Listed agent missing '{field}'. Keys: {list(test_agent.keys())}"
        assert test_agent["triggerId"] == state["test_trigger_id"]
        assert test_agent["actionsId"] == state["test_actions_id"]

    runner.run_test("agent/list — fields: id, name, status, triggerId, actionsId", test_agent_list_fields)

    # ════════════════════════════════════════════
    # Phase 5: Deletion
    # ════════════════════════════════════════════

    def test_agent_delete():
        result = agents_post("/api/v1/agent/delete", {"id": state["test_agent_id"]})
        assert result.get("status") == "Deleted", f"Expected status=Deleted, got {result.get('status')}"
        # Verify gone from list
        list_result = agents_post("/api/v1/agent/list", {"partnerId": PARTNER_ID})
        agent_ids = [a["id"] for a in list_result.get("objects", [])]
        assert state["test_agent_id"] not in agent_ids
        state["agent_deleted"] = True
        print(f"    Deleted agent: {state['test_agent_id']}")

    runner.run_test("agent/delete — removed from list", test_agent_delete)

    def test_explicit_cleanup():
        """Trigger and actions must be deleted explicitly (not cascade-deleted with agent)."""
        trigger_result = agents_post("/api/v1/trigger/delete", {"id": state["test_trigger_id"]})
        assert trigger_result.get("status") == "Deleted", (
            f"Trigger not deletable — may have been cascade-deleted. Response: {trigger_result}"
        )
        actions_result = agents_post("/api/v1/actions/delete", {"id": state["test_actions_id"]})
        assert actions_result.get("status") == "Deleted", (
            f"Actions not deletable — may have been cascade-deleted. Response: {actions_result}"
        )
        print("    Trigger and actions deleted explicitly (no cascade)")

    runner.run_test("trigger/delete + actions/delete — explicit cleanup required", test_explicit_cleanup)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════

    keep = "--keep" in sys.argv
    if keep:
        print("\n--- Keeping test resources (--keep flag) ---")
        for key, val in state.items():
            if key.endswith("_id") and val:
                print(f"    {key} = {val}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


def _safe_delete(resource_type, resource_id):
    try:
        agents_post(f"/api/v1/{resource_type}/delete", {"id": resource_id})
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA AGENTS MANAGER API — End-to-End Validation")
    print(f"{'='*60}\n")
    main()

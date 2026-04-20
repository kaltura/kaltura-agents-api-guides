#!/usr/bin/env python3
"""
End-to-end validation of the Access Control API.

Covers: accessControlProfile CRUD (add/get/list/update/delete),
profile with rules (conditions + actions + contexts),
assigning profile to entry, baseEntry.getContextData,
error handling.
"""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, create_test_entry, delete_test_entry, TestRunner, PARTNER_ID, KS, SERVICE_URL

TS = int(time.time())
state = {}


def main():
    runner = TestRunner("Access Control API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Profile CRUD
    # ════════════════════════════════════════════

    def test_acp_add():
        """Create an access control profile."""
        result = kaltura_post("accessControlProfile", "add", {
            "accessControlProfile[objectType]": "KalturaAccessControlProfile",
            "accessControlProfile[name]": f"API_Test_ACP_{TS}",
            "accessControlProfile[description]": "Test access control profile. Safe to delete.",
        })
        assert result.get("objectType") == "KalturaAccessControlProfile", (
            f"Expected KalturaAccessControlProfile, got {result.get('objectType')}"
        )
        assert result["name"] == f"API_Test_ACP_{TS}"
        assert "id" in result, f"Expected id in response: {result}"
        state["acp_id"] = result["id"]
        runner.register_cleanup(f"access control profile {result['id']}",
                                lambda: _delete_acp(state["acp_id"]))
        print(f"    Created ACP: id={result['id']}, name={result['name']}")

    runner.run_test("accessControlProfile.add — create profile", test_acp_add)

    def test_acp_get():
        """Retrieve access control profile by ID."""
        result = kaltura_post("accessControlProfile", "get", {
            "id": state["acp_id"],
        })
        assert result["id"] == state["acp_id"]
        assert result["name"] == f"API_Test_ACP_{TS}"
        assert result.get("objectType") == "KalturaAccessControlProfile"
        print(f"    Got ACP: id={result['id']}, name={result['name']}")

    runner.run_test("accessControlProfile.get — retrieve by ID", test_acp_get)

    def test_acp_list():
        """List access control profiles and verify ours is included."""
        result = kaltura_post("accessControlProfile", "list", {
            "filter[objectType]": "KalturaAccessControlProfileFilter",
            "filter[idEqual]": state["acp_id"],
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 profile, got {result.get('totalCount')}"
        )
        ids = [p["id"] for p in result.get("objects", [])]
        assert state["acp_id"] in ids, f"Expected ACP {state['acp_id']} in results"
        print(f"    Listed {result['totalCount']} profile(s) matching filter")

    runner.run_test("accessControlProfile.list — filter by ID", test_acp_list)

    def test_acp_update():
        """Update access control profile description."""
        result = kaltura_post("accessControlProfile", "update", {
            "id": state["acp_id"],
            "accessControlProfile[objectType]": "KalturaAccessControlProfile",
            "accessControlProfile[description]": "Updated test ACP description",
        })
        assert result["description"] == "Updated test ACP description", (
            f"Expected updated description, got '{result.get('description')}'"
        )
        assert result["name"] == f"API_Test_ACP_{TS}", (
            f"Name changed unexpectedly: {result.get('name')}"
        )
        print(f"    Updated ACP: description='{result['description']}'")

    runner.run_test("accessControlProfile.update — change description", test_acp_update)

    # ════════════════════════════════════════════
    # Phase 2: Profile with Rules
    # ════════════════════════════════════════════

    def test_acp_add_with_rules():
        """Create a profile with IP condition and block action."""
        result = kaltura_post("accessControlProfile", "add", {
            "accessControlProfile[objectType]": "KalturaAccessControlProfile",
            "accessControlProfile[name]": f"API_Test_ACP_Rules_{TS}",
            "accessControlProfile[description]": "Profile with IP block rule. Safe to delete.",
            "accessControlProfile[rules][0][objectType]": "KalturaRule",
            "accessControlProfile[rules][0][actions][0][objectType]": "KalturaAccessControlBlockAction",
            "accessControlProfile[rules][0][conditions][0][objectType]": "KalturaIpAddressCondition",
            "accessControlProfile[rules][0][conditions][0][not]": 1,
            "accessControlProfile[rules][0][conditions][0][values][0][objectType]": "KalturaStringValue",
            "accessControlProfile[rules][0][conditions][0][values][0][value]": "10.0.0.0/8",
            "accessControlProfile[rules][0][contexts][0][objectType]": "KalturaAccessControlContextTypeHolder",
            "accessControlProfile[rules][0][contexts][0][type]": 1,
            "accessControlProfile[rules][0][message]": "Access restricted to internal network",
        })
        assert result.get("objectType") == "KalturaAccessControlProfile"
        rules = result.get("rules", [])
        if isinstance(rules, list):
            assert len(rules) >= 1, f"Expected at least 1 rule, got {len(rules)}"
            rule = rules[0]
            actions = rule.get("actions", [])
            conditions = rule.get("conditions", [])
            assert len(actions) >= 1, f"Expected at least 1 action, got {len(actions)}"
            assert len(conditions) >= 1, f"Expected at least 1 condition, got {len(conditions)}"
            print(f"    Created ACP with rules: id={result['id']}, "
                  f"rules={len(rules)}, actions={len(actions)}, conditions={len(conditions)}")
        else:
            print(f"    Created ACP with rules: id={result['id']}")
        state["acp_rules_id"] = result["id"]
        runner.register_cleanup(f"rules ACP {result['id']}",
                                lambda: _delete_acp(state["acp_rules_id"]))

    runner.run_test("accessControlProfile.add — profile with IP block rule", test_acp_add_with_rules)

    def test_acp_add_with_preview():
        """Create a profile with preview action (paywall)."""
        result = kaltura_post("accessControlProfile", "add", {
            "accessControlProfile[objectType]": "KalturaAccessControlProfile",
            "accessControlProfile[name]": f"API_Test_ACP_Preview_{TS}",
            "accessControlProfile[description]": "Preview-only profile. Safe to delete.",
            "accessControlProfile[rules][0][objectType]": "KalturaRule",
            "accessControlProfile[rules][0][actions][0][objectType]": "KalturaAccessControlPreviewAction",
            "accessControlProfile[rules][0][actions][0][limit]": 30,
            "accessControlProfile[rules][0][conditions][0][objectType]": "KalturaAuthenticatedCondition",
            "accessControlProfile[rules][0][conditions][0][not]": 1,
        })
        assert result.get("objectType") == "KalturaAccessControlProfile"
        rules = result.get("rules", [])
        if isinstance(rules, list) and len(rules) >= 1:
            action = rules[0].get("actions", [{}])[0]
            assert action.get("objectType") == "KalturaAccessControlPreviewAction", (
                f"Expected preview action, got {action.get('objectType')}"
            )
            assert action.get("limit") == 30, (
                f"Expected preview limit=30, got {action.get('limit')}"
            )
            print(f"    Created preview ACP: id={result['id']}, limit={action.get('limit')}s")
        else:
            print(f"    Created preview ACP: id={result['id']}")
        state["acp_preview_id"] = result["id"]
        runner.register_cleanup(f"preview ACP {result['id']}",
                                lambda: _delete_acp(state["acp_preview_id"]))

    runner.run_test("accessControlProfile.add — preview/paywall rule", test_acp_add_with_preview)

    def test_acp_add_with_country():
        """Create a profile with country geo-restriction."""
        result = kaltura_post("accessControlProfile", "add", {
            "accessControlProfile[objectType]": "KalturaAccessControlProfile",
            "accessControlProfile[name]": f"API_Test_ACP_Geo_{TS}",
            "accessControlProfile[description]": "Country-restricted profile. Safe to delete.",
            "accessControlProfile[rules][0][objectType]": "KalturaRule",
            "accessControlProfile[rules][0][actions][0][objectType]": "KalturaAccessControlBlockAction",
            "accessControlProfile[rules][0][conditions][0][objectType]": "KalturaCountryCondition",
            "accessControlProfile[rules][0][conditions][0][not]": 1,
            "accessControlProfile[rules][0][conditions][0][values][0][objectType]": "KalturaStringValue",
            "accessControlProfile[rules][0][conditions][0][values][0][value]": "US",
            "accessControlProfile[rules][0][conditions][0][values][1][objectType]": "KalturaStringValue",
            "accessControlProfile[rules][0][conditions][0][values][1][value]": "CA",
            "accessControlProfile[rules][0][message]": "Content not available in your region",
        })
        assert result.get("objectType") == "KalturaAccessControlProfile"
        rules = result.get("rules", [])
        if isinstance(rules, list) and len(rules) >= 1:
            cond = rules[0].get("conditions", [{}])[0]
            values = cond.get("values", [])
            print(f"    Created geo ACP: id={result['id']}, "
                  f"condition={cond.get('objectType')}, values={len(values)}")
        else:
            print(f"    Created geo ACP: id={result['id']}")
        state["acp_geo_id"] = result["id"]
        runner.register_cleanup(f"geo ACP {result['id']}",
                                lambda: _delete_acp(state["acp_geo_id"]))

    runner.run_test("accessControlProfile.add — country geo-restriction", test_acp_add_with_country)

    def test_acp_add_with_site():
        """Create a profile with domain/site restriction."""
        result = kaltura_post("accessControlProfile", "add", {
            "accessControlProfile[objectType]": "KalturaAccessControlProfile",
            "accessControlProfile[name]": f"API_Test_ACP_Site_{TS}",
            "accessControlProfile[description]": "Domain-restricted profile. Safe to delete.",
            "accessControlProfile[rules][0][objectType]": "KalturaRule",
            "accessControlProfile[rules][0][actions][0][objectType]": "KalturaAccessControlBlockAction",
            "accessControlProfile[rules][0][conditions][0][objectType]": "KalturaSiteCondition",
            "accessControlProfile[rules][0][conditions][0][not]": 1,
            "accessControlProfile[rules][0][conditions][0][values][0][objectType]": "KalturaStringValue",
            "accessControlProfile[rules][0][conditions][0][values][0][value]": "*.example.com",
        })
        assert result.get("objectType") == "KalturaAccessControlProfile"
        print(f"    Created site ACP: id={result['id']}")
        state["acp_site_id"] = result["id"]
        runner.register_cleanup(f"site ACP {result['id']}",
                                lambda: _delete_acp(state["acp_site_id"]))

    runner.run_test("accessControlProfile.add — domain/site restriction", test_acp_add_with_site)

    # ════════════════════════════════════════════
    # Phase 3: Assign Profile to Entry
    # ════════════════════════════════════════════

    def test_create_test_entry():
        """Create a test entry for access control assignment."""
        entry_id = create_test_entry()
        state["test_entry_id"] = entry_id
        runner.register_cleanup(f"entry {entry_id}",
                                lambda: delete_test_entry(state["test_entry_id"]))
        print(f"    Created test entry: {entry_id}")

    runner.run_test("media.add — create test entry", test_create_test_entry)

    def test_assign_acp_to_entry():
        """Assign access control profile to entry via media.update."""
        result = kaltura_post("media", "update", {
            "entryId": state["test_entry_id"],
            "mediaEntry[objectType]": "KalturaMediaEntry",
            "mediaEntry[accessControlId]": state["acp_id"],
        })
        assert result.get("accessControlId") == state["acp_id"], (
            f"Expected accessControlId={state['acp_id']}, got {result.get('accessControlId')}"
        )
        print(f"    Assigned ACP {state['acp_id']} to entry {state['test_entry_id']}")

    runner.run_test("media.update — assign accessControlId", test_assign_acp_to_entry)

    def test_verify_acp_on_entry():
        """Verify access control profile is set on entry."""
        result = kaltura_post("media", "get", {
            "entryId": state["test_entry_id"],
        })
        assert result.get("accessControlId") == state["acp_id"], (
            f"Expected accessControlId={state['acp_id']}, got {result.get('accessControlId')}"
        )
        print(f"    Verified: entry {state['test_entry_id']} has accessControlId={result.get('accessControlId')}")

    runner.run_test("media.get — verify accessControlId on entry", test_verify_acp_on_entry)

    def test_reassign_acp_on_entry():
        """Reassign a different access control profile to entry."""
        result = kaltura_post("media", "update", {
            "entryId": state["test_entry_id"],
            "mediaEntry[objectType]": "KalturaMediaEntry",
            "mediaEntry[accessControlId]": state.get("acp_rules_id", state["acp_id"]),
        })
        acp_id = result.get("accessControlId")
        print(f"    Reassigned ACP on entry, accessControlId={acp_id}")

    runner.run_test("media.update — reassign accessControlId", test_reassign_acp_on_entry)

    # ════════════════════════════════════════════
    # Phase 4: baseEntry.getContextData
    # ════════════════════════════════════════════

    def test_get_context_data():
        """Get context data for an entry to check scheduling and access control."""
        result = kaltura_post("baseEntry", "getContextData", {
            "entryId": state["test_entry_id"],
            "contextDataParams[objectType]": "KalturaEntryContextDataParams",
        })
        assert "isScheduledNow" in result or "objectType" in result, (
            f"Expected context data response, got: {result}"
        )
        is_scheduled = result.get("isScheduledNow")
        actions = result.get("actions", [])
        messages = result.get("messages", [])
        print(f"    Context data: isScheduledNow={is_scheduled}, "
              f"actions={len(actions) if isinstance(actions, list) else 'N/A'}, "
              f"messages={len(messages) if isinstance(messages, list) else 'N/A'}")

    runner.run_test("baseEntry.getContextData — check scheduling and access", test_get_context_data)

    # ════════════════════════════════════════════
    # Phase 5: Error Handling
    # ════════════════════════════════════════════

    def test_acp_get_invalid():
        """Getting a non-existent profile returns an error."""
        try:
            kaltura_post("accessControlProfile", "get", {
                "id": 999999999,
            })
            raise AssertionError("Expected error for invalid ACP ID")
        except Exception as e:
            err = str(e)
            assert "NOT_FOUND" in err.upper() or "ACCESS_CONTROL" in err.upper(), (
                f"Expected not-found error, got: {err}"
            )
        print("    Correctly returned error for invalid ACP ID")

    runner.run_test("accessControlProfile.get — error for invalid ID", test_acp_get_invalid)

    # ════════════════════════════════════════════
    # Phase 6: Cleanup
    # ════════════════════════════════════════════

    def test_delete_test_entry():
        """Delete the test media entry."""
        delete_test_entry(state["test_entry_id"])
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if f"entry {state['test_entry_id']}" not in label
        ]
        print(f"    Deleted entry: {state['test_entry_id']}")

    runner.run_test("media.delete — clean up test entry", test_delete_test_entry)

    def test_acp_delete():
        """Delete the basic access control profile."""
        kaltura_post("accessControlProfile", "delete", {
            "id": state["acp_id"],
        })
        try:
            kaltura_post("accessControlProfile", "get", {
                "id": state["acp_id"],
            })
            raise AssertionError("Expected error after deleting ACP")
        except Exception as e:
            err = str(e)
            assert "NOT_FOUND" in err.upper() or "INVALID" in err.upper() or "not found" in err.lower(), (
                f"Expected not-found error, got: {err}"
            )
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if f"access control profile {state['acp_id']}" not in label
        ]
        print(f"    Deleted ACP: {state['acp_id']}")

    runner.run_test("accessControlProfile.delete — remove profile", test_acp_delete)

    def test_delete_rules_profiles():
        """Delete the rule-based profiles."""
        for key, label in [("acp_rules_id", "rules"), ("acp_preview_id", "preview"),
                           ("acp_geo_id", "geo"), ("acp_site_id", "site")]:
            if key in state:
                try:
                    kaltura_post("accessControlProfile", "delete", {"id": state[key]})
                    print(f"    Deleted {label} ACP: {state[key]}")
                except Exception:
                    print(f"    Already deleted or error cleaning {label} ACP: {state[key]}")
                runner._cleanup_actions = [
                    (lbl, fn) for lbl, fn in runner._cleanup_actions
                    if f"{label} ACP {state[key]}" not in lbl
                ]

    runner.run_test("accessControlProfile.delete — clean up rule-based profiles", test_delete_rules_profiles)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print(f"\n--keep flag set. Resources preserved:")
        print(f"  Basic ACP ID: {state.get('acp_id')}")
        print(f"  Rules ACP ID: {state.get('acp_rules_id')}")
        print(f"  Preview ACP ID: {state.get('acp_preview_id')}")
        print(f"  Geo ACP ID: {state.get('acp_geo_id')}")
        print(f"  Site ACP ID: {state.get('acp_site_id')}")
        print(f"  Test Entry ID: {state.get('test_entry_id')}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


def _delete_acp(acp_id):
    try:
        kaltura_post("accessControlProfile", "delete", {"id": acp_id})
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA ACCESS CONTROL — End-to-End API Validation")
    print(f"{'='*60}\n")
    main()

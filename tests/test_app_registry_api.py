#!/usr/bin/env python3
"""
End-to-end validation of the App Registry API against the live API.

Covers: add (basic + domain + duplicate detection), get, update (name + versioning),
enable/disable (toggle + idempotent), list (filter + pagination + empty filter),
findByOrganizationDomain (match + domain whitespace stripping), delete (+ verify gone),
error responses (OBJECT_NOT_FOUND, duplicate appCustomId).
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import (
    app_registry_post, TestRunner, PARTNER_ID, KS,
    APP_REGISTRY_URL,
)

state = {}
TS = int(time.time())


def main():
    runner = TestRunner("App Registry API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Create
    # ════════════════════════════════════════════
    def test_add_basic():
        """Register a basic app instance and verify defaults."""
        result = app_registry_post("add", {
            "appCustomId": f"test-app-{TS}",
            "appType": "test",
            "appCustomName": f"API Doc Test App {TS}",
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result["status"] == "enabled", f"Expected status=enabled, got {result.get('status')}"
        assert result["version"] == 0, f"Expected version=0, got {result.get('version')}"
        assert result.get("objectType") == "App", f"Expected objectType=App, got {result.get('objectType')}"
        assert result.get("createdAt") is not None, \
            f"Expected createdAt in response, got None"
        state["app_id"] = result["id"]
        state["app_custom_id"] = f"test-app-{TS}"
        runner.register_cleanup(
            f"app {result['id']}",
            lambda: app_registry_post("delete", {"id": state["app_id"]}),
        )
        print(f"    Created: {result['id']} (type={result['appType']}, version={result['version']})")

    runner.run_test("app-registry.add — register basic app", test_add_basic)

    def test_add_with_domain():
        """Register an app with organizationDomain and verify whitespace stripping."""
        result = app_registry_post("add", {
            "appCustomId": f"test-domain-app-{TS}",
            "appType": "test",
            "appCustomName": f"Domain App {TS}",
            "organizationDomain": {
                "organizationId": f"org-test-{TS}",
                "domain": f" test-{TS}.example.com ",  # whitespace should be stripped
            },
        })
        assert "id" in result, f"Expected id in response: {result}"
        domain = result.get("organizationDomain", {}).get("domain", "")
        assert " " not in domain, f"Expected whitespace stripped from domain, got '{domain}'"
        assert f"test-{TS}.example.com" in domain, f"Expected domain in response: {result}"
        state["domain_app_id"] = result["id"]
        state["domain"] = f"test-{TS}.example.com"
        state["org_id"] = f"org-test-{TS}"
        runner.register_cleanup(
            f"domain app {result['id']}",
            lambda: app_registry_post("delete", {"id": state["domain_app_id"]}),
        )
        print(f"    Created: {result['id']} (domain={domain})")

    runner.run_test("app-registry.add — domain with whitespace stripping", test_add_with_domain)

    def test_add_duplicate_custom_id():
        """Attempting to add with a duplicate appCustomId returns an error."""
        try:
            app_registry_post("add", {
                "appCustomId": state["app_custom_id"],  # already used
                "appType": "test",
                "appCustomName": "Duplicate Test",
            })
            raise AssertionError("Expected error for duplicate appCustomId, got success")
        except Exception as e:
            err = str(e)
            assert "APP_REGISTRY_ALREADY_EXISTS_WITH_THIS_APP_CUSTOM_ID" in err \
                or "already exists" in err.lower(), \
                f"Expected duplicate error, got: {err}"
        print(f"    Correctly rejected duplicate appCustomId '{state['app_custom_id']}'")

    runner.run_test("app-registry.add — duplicate appCustomId rejected", test_add_duplicate_custom_id)

    # ════════════════════════════════════════════
    # Phase 2: Read
    # ════════════════════════════════════════════
    def test_get():
        """Retrieve app by ID and verify all fields."""
        result = app_registry_post("get", {"id": state["app_id"]})
        assert result["id"] == state["app_id"], f"ID mismatch: {result.get('id')}"
        assert result["appCustomId"] == state["app_custom_id"], \
            f"appCustomId mismatch: {result.get('appCustomId')}"
        assert result["appType"] == "test", f"appType mismatch: {result.get('appType')}"
        assert result["status"] == "enabled", f"status mismatch: {result.get('status')}"
        assert result.get("objectType") == "App", f"objectType mismatch: {result.get('objectType')}"
        print(f"    Got: {result['id']}, type={result['appType']}, version={result['version']}")

    runner.run_test("app-registry.get — retrieve by ID", test_get)

    def test_get_not_found():
        """Getting a non-existent ID returns OBJECT_NOT_FOUND."""
        try:
            app_registry_post("get", {"id": "000000000000000000000000"})
            raise AssertionError("Expected OBJECT_NOT_FOUND, got success")
        except Exception as e:
            assert "OBJECT_NOT_FOUND" in str(e) or "not found" in str(e).lower(), \
                f"Expected OBJECT_NOT_FOUND, got: {e}"
        print("    Correctly returned OBJECT_NOT_FOUND for non-existent ID")

    runner.run_test("app-registry.get — OBJECT_NOT_FOUND for invalid ID", test_get_not_found)

    def test_list_with_filter():
        """List apps with type+status filter, verify our app is included."""
        result = app_registry_post("list", {
            "filter": {"appType": "test", "status": "enabled"},
            "pager": {"offset": 0, "limit": 50},
        })
        assert "objects" in result, f"Expected objects in response: {result}"
        assert "totalCount" in result, f"Expected totalCount in response: {result}"
        ids = [obj["id"] for obj in result["objects"]]
        assert state["app_id"] in ids, f"Expected {state['app_id']} in list results"
        for obj in result["objects"]:
            assert obj.get("objectType") == "App", f"Expected objectType=App in list items"
        print(f"    Listed {result['totalCount']} total, {len(result['objects'])} returned")

    runner.run_test("app-registry.list — filter by type and status", test_list_with_filter)

    def test_list_empty_filter():
        """List with no filter returns all apps for the partner."""
        result = app_registry_post("list", {})
        assert "objects" in result, f"Expected objects: {result}"
        assert result["totalCount"] >= 2, \
            f"Expected at least 2 apps (created 2 in setup), got {result['totalCount']}"
        print(f"    All apps: {result['totalCount']} total (no filter)")

    runner.run_test("app-registry.list — no filter returns all apps", test_list_empty_filter)

    def test_list_pagination():
        """List with limit=1 returns exactly 1 object but correct totalCount."""
        result = app_registry_post("list", {
            "filter": {"appType": "test", "status": "enabled"},
            "pager": {"offset": 0, "limit": 1},
        })
        assert len(result["objects"]) <= 1, \
            f"Expected max 1 object with limit=1, got {len(result['objects'])}"
        assert result["totalCount"] >= 2, \
            f"Expected totalCount >= 2 (we created 2), got {result['totalCount']}"
        print(f"    Pagination: 1 returned, {result['totalCount']} total")

    runner.run_test("app-registry.list — pagination limit=1", test_list_pagination)

    def test_list_id_in_filter():
        """List with idIn filter returns only the specified apps."""
        result = app_registry_post("list", {
            "filter": {"idIn": [state["app_id"], state["domain_app_id"]]},
        })
        ids = [obj["id"] for obj in result["objects"]]
        assert state["app_id"] in ids, f"Expected {state['app_id']} in results"
        assert state["domain_app_id"] in ids, f"Expected {state['domain_app_id']} in results"
        assert result["totalCount"] == 2, f"Expected totalCount=2, got {result['totalCount']}"
        print(f"    idIn filter: returned {result['totalCount']} apps")

    runner.run_test("app-registry.list — idIn filter", test_list_id_in_filter)

    def test_list_app_custom_id_in():
        """List with appCustomIdIn filter — the virtualEventId→appGuid lookup pattern."""
        result = app_registry_post("list", {
            "filter": {"appCustomIdIn": [state["app_custom_id"]]},
        })
        assert result["totalCount"] >= 1, \
            f"Expected at least 1 result for appCustomIdIn, got {result['totalCount']}"
        ids = [obj["id"] for obj in result["objects"]]
        assert state["app_id"] in ids, \
            f"Expected {state['app_id']} in appCustomIdIn results"
        # Verify the returned app has the correct appCustomId
        matched = [obj for obj in result["objects"] if obj["id"] == state["app_id"]][0]
        assert matched["appCustomId"] == state["app_custom_id"], \
            f"appCustomId mismatch: {matched.get('appCustomId')}"
        print(f"    appCustomIdIn filter: found app {state['app_id']} via custom ID '{state['app_custom_id']}'")

    runner.run_test("app-registry.list — appCustomIdIn filter (event ID lookup)", test_list_app_custom_id_in)

    def test_list_date_filter():
        """List with updatedAtGreaterThanOrEqual for incremental sync pattern."""
        # Use a timestamp from before our test apps were created
        from datetime import datetime, timezone, timedelta
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = app_registry_post("list", {
            "filter": {
                "updatedAtGreaterThanOrEqual": past,
                "appType": "test",
            },
        })
        assert result["totalCount"] >= 1, \
            f"Expected at least 1 app updated in last hour, got {result['totalCount']}"
        ids = [obj["id"] for obj in result["objects"]]
        assert state["app_id"] in ids, \
            f"Expected {state['app_id']} in date-filtered results"
        print(f"    Date filter: {result['totalCount']} app(s) updated since {past}")

    runner.run_test("app-registry.list — updatedAt date filter (incremental sync)", test_list_date_filter)

    def test_find_by_domain():
        """Find app by organization domain."""
        result = app_registry_post("findByOrganizationDomain", {
            "domain": state["domain"],
            "appType": "test",
        })
        assert "objects" in result, f"Expected objects in response: {result}"
        ids = [obj["id"] for obj in result["objects"]]
        assert state["domain_app_id"] in ids, \
            f"Expected {state['domain_app_id']} in domain search results"
        print(f"    Found {result['totalCount']} app(s) for domain {state['domain']}")

    runner.run_test("app-registry.findByOrganizationDomain — lookup", test_find_by_domain)

    # ════════════════════════════════════════════
    # Phase 3: Update
    # ════════════════════════════════════════════
    def test_update_name():
        """Update appCustomName and verify version increment."""
        before = app_registry_post("get", {"id": state["app_id"]})
        result = app_registry_post("update", {
            "id": state["app_id"],
            "appCustomName": "Updated Test App Name",
        })
        assert result["appCustomName"] == "Updated Test App Name", \
            f"Expected updated name, got {result.get('appCustomName')}"
        assert result["version"] == before["version"] + 1, \
            f"Expected version {before['version'] + 1}, got {result.get('version')}"
        assert result.get("updatedAt") is not None, \
            f"Expected updatedAt in response"
        # appType should be unchanged
        assert result["appType"] == before["appType"], \
            f"appType changed unexpectedly: {result.get('appType')}"
        print(f"    Updated: name='{result['appCustomName']}', version={result['version']}")

    runner.run_test("app-registry.update — change name, verify version+1", test_update_name)

    def test_update_null_ignored():
        """Sending null for a field does not clear it."""
        result = app_registry_post("update", {
            "id": state["app_id"],
            "appCustomName": None,  # should be ignored
        })
        assert result["appCustomName"] == "Updated Test App Name", \
            f"Expected name preserved after null update, got {result.get('appCustomName')}"
        print(f"    Null field ignored, name preserved: '{result['appCustomName']}'")

    runner.run_test("app-registry.update — null fields ignored", test_update_null_ignored)

    # ════════════════════════════════════════════
    # Phase 4: Enable / Disable
    # ════════════════════════════════════════════
    def test_disable():
        """Disable an app and verify status change."""
        before = app_registry_post("get", {"id": state["app_id"]})
        result = app_registry_post("disable", {"id": state["app_id"]})
        assert result["status"] == "disabled", f"Expected disabled, got {result.get('status')}"
        print(f"    Disabled: version {before['version']} → {result['version']}, status={result['status']}")

    runner.run_test("app-registry.disable — status change", test_disable)

    def test_disable_idempotent():
        """Disabling an already-disabled app returns current state without version bump."""
        before = app_registry_post("get", {"id": state["app_id"]})
        result = app_registry_post("disable", {"id": state["app_id"]})
        assert result["version"] == before["version"], \
            f"Expected no version change, got {result['version']} (was {before['version']})"
        assert result["status"] == "disabled", f"Status should still be disabled"
        print(f"    Idempotent: version unchanged at {result['version']}")

    runner.run_test("app-registry.disable — idempotent (no version bump)", test_disable_idempotent)

    def test_enable():
        """Re-enable a disabled app."""
        before = app_registry_post("get", {"id": state["app_id"]})
        result = app_registry_post("enable", {"id": state["app_id"]})
        assert result["status"] == "enabled", f"Expected enabled, got {result.get('status')}"
        print(f"    Enabled: version {before['version']} → {result['version']}, status={result['status']}")

    runner.run_test("app-registry.enable — re-enable", test_enable)

    def test_enable_idempotent():
        """Enabling an already-enabled app returns current state without version bump."""
        before = app_registry_post("get", {"id": state["app_id"]})
        result = app_registry_post("enable", {"id": state["app_id"]})
        assert result["version"] == before["version"], \
            f"Expected no version change on idempotent enable"
        print(f"    Idempotent: version unchanged at {result['version']}")

    runner.run_test("app-registry.enable — idempotent (no version bump)", test_enable_idempotent)

    # ════════════════════════════════════════════
    # Phase 5: Delete
    # ════════════════════════════════════════════
    def test_delete_and_verify():
        """Delete the domain app and verify it's gone from get and list."""
        app_registry_post("delete", {"id": state["domain_app_id"]})

        # Verify get returns error
        try:
            app_registry_post("get", {"id": state["domain_app_id"]})
            raise AssertionError("Expected OBJECT_NOT_FOUND after delete")
        except Exception as e:
            assert "OBJECT_NOT_FOUND" in str(e) or "not found" in str(e).lower(), \
                f"Expected OBJECT_NOT_FOUND, got: {e}"

        # Verify excluded from list
        result = app_registry_post("list", {
            "filter": {"idIn": [state["domain_app_id"]]},
        })
        assert result["totalCount"] == 0, \
            f"Expected 0 results for deleted app, got {result['totalCount']}"

        # Remove from cleanup
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if "domain app" not in label
        ]
        print(f"    Deleted {state['domain_app_id']} — verified gone from get and list")

    runner.run_test("app-registry.delete — permanent removal verified", test_delete_and_verify)

    def test_delete_not_found():
        """Deleting a non-existent ID returns OBJECT_NOT_FOUND."""
        try:
            app_registry_post("delete", {"id": "000000000000000000000000"})
            raise AssertionError("Expected OBJECT_NOT_FOUND")
        except Exception as e:
            assert "OBJECT_NOT_FOUND" in str(e) or "not found" in str(e).lower(), \
                f"Expected OBJECT_NOT_FOUND, got: {e}"
        print("    Correctly returned OBJECT_NOT_FOUND for non-existent ID")

    runner.run_test("app-registry.delete — OBJECT_NOT_FOUND for invalid ID", test_delete_not_found)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print(f"\n--keep flag set. Resources preserved:")
        print(f"  App ID: {state.get('app_id')}")
        print(f"\n  Clean up manually:")
        app_id = state.get('app_id')
        print(f'    curl -X POST "{APP_REGISTRY_URL}/app-registry/delete" \\')
        print(f'      -H "Authorization: Bearer $KS" \\')
        print(f'      -H "Content-Type: application/json" \\')
        print(f'      -d \'{{"id": "{app_id}"}}\'')
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

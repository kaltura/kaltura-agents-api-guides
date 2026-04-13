#!/usr/bin/env python3
"""
End-to-end validation of the Categories & Access Control API against the live API.

Covers: category CRUD (add/get/list/update/delete), category hierarchy (parentId, fullName),
categoryUser (add/get/list/update/delete), categoryEntry (add/list/delete),
accessControlProfile CRUD (add/get/list/update/delete), error handling.

Note: Category operations require a KS with 'disableentitlement' privilege to avoid
NOT_ENTITLED_TO_UPDATE_CATEGORY errors on accounts with entitlement enabled.
"""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, create_test_entry, delete_test_entry, TestRunner, PARTNER_ID, KS, SERVICE_URL

TS = int(time.time())
state = {}

ADMIN_SECRET = os.environ.get("KALTURA_ADMIN_SECRET", "")


def _generate_category_ks():
    """Generate an ADMIN KS with disableentitlement for category operations."""
    if not ADMIN_SECRET:
        print("  [WARN] KALTURA_ADMIN_SECRET not set — using default KS (may fail on entitled accounts)")
        return KS
    resp = requests.post(
        f"{SERVICE_URL}/service/session/action/start",
        data={
            "partnerId": PARTNER_ID,
            "secret": ADMIN_SECRET,
            "type": 2,
            "expiry": 86400,
            "privileges": "disableentitlement",
            "format": 1,
        },
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    if isinstance(result, str):
        return result
    raise Exception(f"Failed to generate category KS: {result}")


def _cat_post(service, action, params=None):
    """POST to Kaltura API using the category KS (with disableentitlement)."""
    data = {"ks": state["cat_ks"], "format": 1}
    if params:
        data.update(params)
    resp = requests.post(
        f"{SERVICE_URL}/service/{service}/action/{action}",
        data=data,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
        raise Exception(f"Kaltura API error: {result.get('message')} (code: {result.get('code')})")
    return result


def main():
    runner = TestRunner("Categories & Access Control API — E2E Validation")

    # Generate a KS with disableentitlement for category operations
    state["cat_ks"] = _generate_category_ks()
    if ADMIN_SECRET:
        print("  Using KS with disableentitlement for category operations\n")
    else:
        print("  Using default KS (KALTURA_ADMIN_SECRET not set)\n")

    # ════════════════════════════════════════════
    # Phase 1: Category CRUD
    # ════════════════════════════════════════════

    def test_category_add_parent():
        """Create a parent category and verify defaults."""
        result = _cat_post("category", "add", {
            "category[objectType]": "KalturaCategory",
            "category[name]": f"API_Test_Parent_{TS}",
            "category[description]": "Test category for API doc validation. Safe to delete.",
            "category[tags]": "api-test",
            "category[privacy]": 1,              # ALL
            "category[appearInList]": 1,          # PARTNER_ONLY
            "category[contributionPolicy]": 1,    # ALL
            "category[inheritanceType]": 2,       # MANUAL
        })
        assert result.get("objectType") == "KalturaCategory", (
            f"Expected KalturaCategory, got {result.get('objectType')}"
        )
        assert result["name"] == f"API_Test_Parent_{TS}"
        assert result["status"] == 2, f"Expected ACTIVE status=2, got {result['status']}"
        assert result.get("parentId") == 0 or result.get("parentId") is None, (
            f"Expected root-level parentId=0, got {result.get('parentId')}"
        )
        state["parent_cat_id"] = result["id"]
        runner.register_cleanup(f"parent category {result['id']}",
                                lambda: _delete_category(state["parent_cat_id"]))
        print(f"    Created parent: id={result['id']}, name={result['name']}")

    runner.run_test("category.add — create parent category", test_category_add_parent)

    def test_category_add_child():
        """Create a child category under the parent."""
        result = _cat_post("category", "add", {
            "category[objectType]": "KalturaCategory",
            "category[name]": f"API_Test_Child_{TS}",
            "category[parentId]": state["parent_cat_id"],
            "category[description]": "Child test category. Safe to delete.",
            "category[tags]": "api-test,child",
            "category[privacy]": 1,
            "category[appearInList]": 1,
            "category[contributionPolicy]": 1,
            "category[inheritanceType]": 2,
        })
        assert result.get("objectType") == "KalturaCategory"
        assert result["name"] == f"API_Test_Child_{TS}"
        assert result["status"] == 2
        assert result.get("parentId") == state["parent_cat_id"], (
            f"Expected parentId={state['parent_cat_id']}, got {result.get('parentId')}"
        )
        state["child_cat_id"] = result["id"]
        runner.register_cleanup(f"child category {result['id']}",
                                lambda: _delete_category(state["child_cat_id"]))
        print(f"    Created child: id={result['id']}, parentId={result.get('parentId')}")

    runner.run_test("category.add — create child category with parentId", test_category_add_child)

    def test_category_hierarchy():
        """Verify fullName and fullIds reflect the hierarchy."""
        result = _cat_post("category", "get", {
            "id": state["child_cat_id"],
        })
        full_name = result.get("fullName", "")
        full_ids = result.get("fullIds", "")
        assert f"API_Test_Parent_{TS}" in full_name, (
            f"Expected parent name in fullName, got '{full_name}'"
        )
        assert f"API_Test_Child_{TS}" in full_name, (
            f"Expected child name in fullName, got '{full_name}'"
        )
        assert str(state["parent_cat_id"]) in full_ids, (
            f"Expected parent ID in fullIds, got '{full_ids}'"
        )
        assert str(state["child_cat_id"]) in full_ids, (
            f"Expected child ID in fullIds, got '{full_ids}'"
        )
        print(f"    Hierarchy: fullName='{full_name}', fullIds='{full_ids}'")

    runner.run_test("category.get — verify fullName/fullIds hierarchy", test_category_hierarchy)

    def test_category_get():
        """Retrieve parent category by ID."""
        result = _cat_post("category", "get", {
            "id": state["parent_cat_id"],
        })
        assert result["id"] == state["parent_cat_id"]
        assert result["name"] == f"API_Test_Parent_{TS}"
        assert result.get("objectType") == "KalturaCategory"
        print(f"    Got: id={result['id']}, name={result['name']}")

    runner.run_test("category.get — retrieve by ID", test_category_get)

    def test_category_list():
        """List categories with filter and verify our categories are included."""
        result = _cat_post("category", "list", {
            "filter[objectType]": "KalturaCategoryFilter",
            "filter[idIn]": f"{state['parent_cat_id']},{state['child_cat_id']}",
        })
        assert result.get("totalCount", 0) >= 2, (
            f"Expected at least 2 categories, got {result.get('totalCount')}"
        )
        ids = [c["id"] for c in result.get("objects", [])]
        assert state["parent_cat_id"] in ids, f"Parent {state['parent_cat_id']} missing from results"
        assert state["child_cat_id"] in ids, f"Child {state['child_cat_id']} missing from results"
        print(f"    Listed {result['totalCount']} category(ies) matching filter")

    runner.run_test("category.list — filter by IDs", test_category_list)

    def test_category_update():
        """Update category description and verify changes."""
        result = _cat_post("category", "update", {
            "id": state["parent_cat_id"],
            "category[objectType]": "KalturaCategory",
            "category[description]": "Updated test category description",
            "category[tags]": "api-test,updated",
        })
        assert result["description"] == "Updated test category description", (
            f"Expected updated description, got '{result.get('description')}'"
        )
        assert "updated" in result.get("tags", ""), (
            f"Expected 'updated' in tags, got '{result.get('tags')}'"
        )
        # Name should be unchanged
        assert result["name"] == f"API_Test_Parent_{TS}", (
            f"Name changed unexpectedly: {result.get('name')}"
        )
        print(f"    Updated: description='{result['description'][:40]}...', tags='{result.get('tags')}'")

    runner.run_test("category.update — change fields, verify unchanged preserved", test_category_update)

    def test_category_move():
        """Create a second parent and move the child under it, then move back."""
        # Create a second parent to use as the move target
        second_parent = _cat_post("category", "add", {
            "category[objectType]": "KalturaCategory",
            "category[name]": f"API_Test_MoveTarget_{TS}",
            "category[description]": "Move target. Safe to delete.",
            "category[privacy]": 1,
            "category[appearInList]": 1,
            "category[contributionPolicy]": 1,
            "category[inheritanceType]": 2,
        })
        state["move_target_id"] = second_parent["id"]
        runner.register_cleanup(f"move target category {second_parent['id']}",
                                lambda: _delete_category(state["move_target_id"]))

        # Move the child under the new parent
        _cat_post("category", "move", {
            "categoryIds": str(state["child_cat_id"]),
            "targetCategoryParentId": second_parent["id"],
        })
        # Verify the move
        child = _cat_post("category", "get", {"id": state["child_cat_id"]})
        assert child.get("parentId") == second_parent["id"], (
            f"Expected parentId={second_parent['id']}, got {child.get('parentId')}"
        )
        print(f"    Moved child {state['child_cat_id']} under {second_parent['id']}")
        # Move it back for cleanup ordering
        _cat_post("category", "move", {
            "categoryIds": str(state["child_cat_id"]),
            "targetCategoryParentId": state["parent_cat_id"],
        })
        print(f"    Moved back under original parent {state['parent_cat_id']}")

    runner.run_test("category.move — reparent child category", test_category_move)

    # ════════════════════════════════════════════
    # Phase 2: Category Membership (categoryUser)
    # ════════════════════════════════════════════

    def test_create_test_user():
        """Create a test user for categoryUser tests."""
        result = kaltura_post("user", "add", {
            "user[objectType]": "KalturaUser",
            "user[id]": f"cat_test_user_{TS}",
            "user[firstName]": "CatTest",
            "user[lastName]": "User",
            "user[email]": f"cat_test_{TS}@example.com",
            "user[type]": 0,
            "user[tags]": "api-test",
        })
        assert result.get("objectType") == "KalturaUser"
        assert result["status"] == 1
        state["test_user_id"] = result["id"]
        runner.register_cleanup(f"user {result['id']}",
                                lambda: _delete_user(state["test_user_id"]))
        print(f"    Created test user: {result['id']}")

    runner.run_test("user.add — create test user for membership tests", test_create_test_user)

    def test_category_user_add():
        """Add the test user to the parent category."""
        result = _cat_post("categoryUser", "add", {
            "categoryUser[objectType]": "KalturaCategoryUser",
            "categoryUser[categoryId]": state["parent_cat_id"],
            "categoryUser[userId]": state["test_user_id"],
            "categoryUser[permissionLevel]": 3,  # MEMBER
        })
        assert result.get("objectType") == "KalturaCategoryUser", (
            f"Expected KalturaCategoryUser, got {result.get('objectType')}"
        )
        assert result["categoryId"] == state["parent_cat_id"]
        assert result["userId"] == state["test_user_id"]
        assert result["status"] == 1, f"Expected ACTIVE status=1, got {result['status']}"
        print(f"    Added user '{state['test_user_id']}' to category {state['parent_cat_id']}, permissionLevel={result.get('permissionLevel')}")

    runner.run_test("categoryUser.add — add member to category", test_category_user_add)

    def test_category_user_get():
        """Retrieve category user membership."""
        result = _cat_post("categoryUser", "get", {
            "categoryId": state["parent_cat_id"],
            "userId": state["test_user_id"],
        })
        assert result["categoryId"] == state["parent_cat_id"]
        assert result["userId"] == state["test_user_id"]
        assert result.get("objectType") == "KalturaCategoryUser"
        print(f"    Got membership: categoryId={result['categoryId']}, userId={result['userId']}, permissionLevel={result.get('permissionLevel')}")

    runner.run_test("categoryUser.get — retrieve membership", test_category_user_get)

    def test_category_user_list():
        """List members of the parent category."""
        result = _cat_post("categoryUser", "list", {
            "filter[objectType]": "KalturaCategoryUserFilter",
            "filter[categoryIdEqual]": state["parent_cat_id"],
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 member, got {result.get('totalCount')}"
        )
        user_ids = [cu["userId"] for cu in result.get("objects", [])]
        assert state["test_user_id"] in user_ids, (
            f"Expected {state['test_user_id']} in members, got {user_ids}"
        )
        print(f"    Category {state['parent_cat_id']} has {result['totalCount']} member(s)")

    runner.run_test("categoryUser.list — list category members", test_category_user_list)

    def test_category_user_update():
        """Update member permission level from MEMBER to CONTRIBUTOR."""
        result = _cat_post("categoryUser", "update", {
            "categoryId": state["parent_cat_id"],
            "userId": state["test_user_id"],
            "categoryUser[objectType]": "KalturaCategoryUser",
            "categoryUser[permissionLevel]": 2,  # CONTRIBUTOR
            "override": 1,  # Allow overriding manual changes
        })
        assert result.get("permissionLevel") == 2, (
            f"Expected permissionLevel=2 (CONTRIBUTOR), got {result.get('permissionLevel')}"
        )
        print(f"    Updated permissionLevel to {result.get('permissionLevel')} (CONTRIBUTOR)")

    runner.run_test("categoryUser.update — change permission level", test_category_user_update)

    def test_category_user_delete():
        """Remove the test user from the category."""
        _cat_post("categoryUser", "delete", {
            "categoryId": state["parent_cat_id"],
            "userId": state["test_user_id"],
        })
        # Verify removal by listing
        result = _cat_post("categoryUser", "list", {
            "filter[objectType]": "KalturaCategoryUserFilter",
            "filter[categoryIdEqual]": state["parent_cat_id"],
            "filter[userIdEqual]": state["test_user_id"],
        })
        assert result.get("totalCount", 0) == 0, (
            f"Expected 0 members after delete, got {result.get('totalCount')}"
        )
        print(f"    Removed user '{state['test_user_id']}' from category {state['parent_cat_id']}")

    runner.run_test("categoryUser.delete — remove member", test_category_user_delete)

    # ════════════════════════════════════════════
    # Phase 3: Content Assignment (categoryEntry)
    # ════════════════════════════════════════════

    def test_create_test_entry():
        """Create a test media entry for categoryEntry tests."""
        entry_id = create_test_entry()
        state["test_entry_id"] = entry_id
        runner.register_cleanup(f"entry {entry_id}",
                                lambda: delete_test_entry(state["test_entry_id"]))
        print(f"    Created test entry: {entry_id}")

    runner.run_test("media.add — create test entry", test_create_test_entry)

    def test_category_entry_add():
        """Assign the test entry to the parent category."""
        result = _cat_post("categoryEntry", "add", {
            "categoryEntry[objectType]": "KalturaCategoryEntry",
            "categoryEntry[categoryId]": state["parent_cat_id"],
            "categoryEntry[entryId]": state["test_entry_id"],
        })
        assert result.get("objectType") == "KalturaCategoryEntry", (
            f"Expected KalturaCategoryEntry, got {result.get('objectType')}"
        )
        assert result["categoryId"] == state["parent_cat_id"]
        assert result["entryId"] == state["test_entry_id"]
        assert result.get("status") in (1, 2), (
            f"Expected status 1 (ACTIVE) or 2 (PENDING), got {result.get('status')}"
        )
        print(f"    Assigned entry '{state['test_entry_id']}' to category {state['parent_cat_id']}, status={result.get('status')}")

    runner.run_test("categoryEntry.add — assign entry to category", test_category_entry_add)

    def test_category_entry_list():
        """List entries in the parent category."""
        result = _cat_post("categoryEntry", "list", {
            "filter[objectType]": "KalturaCategoryEntryFilter",
            "filter[categoryIdEqual]": state["parent_cat_id"],
        })
        assert result.get("totalCount", 0) >= 1, (
            f"Expected at least 1 entry, got {result.get('totalCount')}"
        )
        entry_ids = [ce["entryId"] for ce in result.get("objects", [])]
        assert state["test_entry_id"] in entry_ids, (
            f"Expected {state['test_entry_id']} in category entries, got {entry_ids}"
        )
        print(f"    Category {state['parent_cat_id']} has {result['totalCount']} entry(ies)")

    runner.run_test("categoryEntry.list — list entries in category", test_category_entry_list)

    def test_category_entry_delete():
        """Remove the entry from the category."""
        _cat_post("categoryEntry", "delete", {
            "entryId": state["test_entry_id"],
            "categoryId": state["parent_cat_id"],
        })
        # Verify removal
        result = _cat_post("categoryEntry", "list", {
            "filter[objectType]": "KalturaCategoryEntryFilter",
            "filter[categoryIdEqual]": state["parent_cat_id"],
            "filter[entryIdEqual]": state["test_entry_id"],
        })
        assert result.get("totalCount", 0) == 0, (
            f"Expected 0 entries after delete, got {result.get('totalCount')}"
        )
        print(f"    Removed entry '{state['test_entry_id']}' from category {state['parent_cat_id']}")

    runner.run_test("categoryEntry.delete — remove entry from category", test_category_entry_delete)

    # ════════════════════════════════════════════
    # Phase 4: Access Control Profiles
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
        # Name should be unchanged
        assert result["name"] == f"API_Test_ACP_{TS}", (
            f"Name changed unexpectedly: {result.get('name')}"
        )
        print(f"    Updated ACP: description='{result['description']}'")

    runner.run_test("accessControlProfile.update — change description", test_acp_update)

    def test_acp_delete():
        """Delete access control profile."""
        kaltura_post("accessControlProfile", "delete", {
            "id": state["acp_id"],
        })
        # Verify deletion by trying to get it
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

    # ════════════════════════════════════════════
    # Phase 5: Error Handling
    # ════════════════════════════════════════════

    def test_category_get_invalid():
        """Getting a non-existent category returns an error."""
        try:
            _cat_post("category", "get", {
                "id": 999999999,
            })
            raise AssertionError("Expected error for invalid category ID")
        except Exception as e:
            err = str(e)
            assert "NOT_FOUND" in err.upper() or "CATEGORY" in err.upper(), (
                f"Expected category not found error, got: {err}"
            )
        print("    Correctly returned error for invalid category ID")

    runner.run_test("category.get — error for invalid ID", test_category_get_invalid)

    def test_category_entry_add_invalid():
        """Adding an entry with an invalid entry ID returns an error."""
        try:
            _cat_post("categoryEntry", "add", {
                "categoryEntry[objectType]": "KalturaCategoryEntry",
                "categoryEntry[categoryId]": state["parent_cat_id"],
                "categoryEntry[entryId]": f"invalid_entry_{TS}",
            })
            raise AssertionError("Expected error for invalid entry ID")
        except Exception as e:
            err = str(e)
            assert "INVALID" in err.upper() or "NOT_FOUND" in err.upper() or "ENTRY" in err.upper(), (
                f"Expected invalid entry error, got: {err}"
            )
        print("    Correctly returned error for invalid entry ID")

    runner.run_test("categoryEntry.add — error for invalid entry ID", test_category_entry_add_invalid)

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

    def test_delete_child_category():
        """Delete the child category first (before parent)."""
        _cat_post("category", "delete", {"id": state["child_cat_id"]})
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if f"child category {state['child_cat_id']}" not in label
        ]
        print(f"    Deleted child category: {state['child_cat_id']}")

    runner.run_test("category.delete — delete child category", test_delete_child_category)

    def test_delete_parent_category():
        """Delete the parent category."""
        _cat_post("category", "delete", {"id": state["parent_cat_id"]})
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if f"parent category {state['parent_cat_id']}" not in label
        ]
        print(f"    Deleted parent category: {state['parent_cat_id']}")

    runner.run_test("category.delete — delete parent category", test_delete_parent_category)

    def test_delete_test_user():
        """Delete the test user."""
        result = kaltura_post("user", "delete", {"userId": state["test_user_id"]})
        assert result["status"] == 2, f"Expected DELETED status=2, got {result['status']}"
        runner._cleanup_actions = [
            (label, fn) for label, fn in runner._cleanup_actions
            if f"user {state['test_user_id']}" not in label
        ]
        print(f"    Deleted user: {state['test_user_id']}, status={result['status']}")

    runner.run_test("user.delete — clean up test user", test_delete_test_user)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print(f"\n--keep flag set. Resources preserved:")
        print(f"  Parent Category ID: {state.get('parent_cat_id')}")
        print(f"  Child Category ID: {state.get('child_cat_id')}")
        print(f"  Test User ID: {state.get('test_user_id')}")
        print(f"  Test Entry ID: {state.get('test_entry_id')}")
        print(f"  Access Control Profile ID: {state.get('acp_id')}")
        print(f"\n  Manual cleanup:")
        print(f"    category.delete id={state.get('child_cat_id')}")
        print(f"    category.delete id={state.get('parent_cat_id')}")
        print(f"    user.delete userId={state.get('test_user_id')}")
        print(f"    media.delete entryId={state.get('test_entry_id')}")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


def _delete_category(category_id):
    try:
        _cat_post("category", "delete", {"id": category_id})
    except Exception:
        pass


def _delete_user(user_id):
    try:
        kaltura_post("user", "delete", {"userId": user_id})
    except Exception:
        pass


def _delete_acp(acp_id):
    try:
        kaltura_post("accessControlProfile", "delete", {"id": acp_id})
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  KALTURA CATEGORIES & ACCESS CONTROL — End-to-End Validation")
    print(f"{'='*60}\n")
    main()
